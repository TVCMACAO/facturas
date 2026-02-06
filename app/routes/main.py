from flask import render_template, flash, redirect, url_for, request, Blueprint, current_app, send_from_directory
from app import db, mail
from app.forms import LoginForm, RegistrationForm, RequestPasswordResetForm, ResetPasswordForm
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User, Client, Product, Quote, Invoice, InvoiceItem, CreditNote, PasswordResetToken # Import new models
from urllib.parse import urlsplit
from app.decorators import role_required # Import role_required
import os # Import os module
from datetime import date, timedelta, datetime
from sqlalchemy import func, and_, case, cast, Integer
from config import Config
import secrets
from flask_mail import Message

main = Blueprint('main', __name__)

@main.route('/', methods=['GET', 'POST'])
@main.route('/index', methods=['GET', 'POST'])
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Usuario o contraseña inválidos', 'danger')
            return redirect(url_for('main.index'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('main.dashboard')
        flash('¡Has iniciado sesión correctamente!', 'success')
        return redirect(next_page)
    return render_template('index.html', title='Inicio', form=form)

@main.route('/login', methods=['GET', 'POST'])
def login():
    # Redirigir a index que ahora muestra el formulario de login
    return redirect(url_for('main.index'))

@main.route('/logout')
def logout():
    logout_user()
    flash('Has cerrado la sesión.', 'info')
    return redirect(url_for('main.index'))

@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(name=form.name.data, username=form.username.data, email=form.email.data) # Modified line
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('¡Felicidades, ahora eres un usuario registrado!', 'success')
        return redirect(url_for('main.login'))
    else:
        pass # Removed debug prints
    return render_template('register.html', title='Registro', form=form)

@main.route('/dashboard')
@login_required
@role_required(['admin'])
def dashboard():
    try:
        today = date.today()

        # --- 1. Métricas Adicionales (nuevas tarjetas) ---
        # Cotizaciones Pendientes (status='pendiente')
        cotizaciones_pendientes = Quote.query.filter_by(status='pendiente').count()

        # Facturas Vencidas (due_date < today and status='no_pagada')
        facturas_vencidas = Invoice.query.filter(
            Invoice.due_date < today,
            Invoice.status == 'no_pagada'
        ).count()

        # Productos con Stock Bajo (stock < 5)
        umbral_stock_bajo = 5
        productos_stock_bajo_count = Product.query.filter(Product.stock < umbral_stock_bajo).count()

        # Ventas del Mes Actual vs Anterior - Separar subtotal, impuestos y descuentos
        start_of_current_month = today.replace(day=1)
        
        # Ventas totales (con impuestos)
        ventas_mes_actual = db.session.query(func.sum(Invoice.total_amount)).filter(
            Invoice.date >= start_of_current_month,
            Invoice.status == 'pagada'
        ).scalar() or 0
        
        # Subtotal (sin impuestos, después de descuentos)
        ventas_netas_mes_actual = db.session.query(
            func.sum(Invoice.subtotal - Invoice.discount_amount)
        ).filter(
            Invoice.date >= start_of_current_month,
            Invoice.status == 'pagada'
        ).scalar() or 0
        
        # Impuestos recaudados del mes
        impuestos_mes_actual = db.session.query(func.sum(Invoice.tax_amount)).filter(
            Invoice.date >= start_of_current_month,
            Invoice.status == 'pagada'
        ).scalar() or 0
        
        # Descuentos otorgados del mes
        descuentos_mes_actual = db.session.query(func.sum(Invoice.discount_amount)).filter(
            Invoice.date >= start_of_current_month,
            Invoice.status == 'pagada'
        ).scalar() or 0

        # Sales for previous month
        end_of_previous_month = start_of_current_month - timedelta(days=1)
        start_of_previous_month = end_of_previous_month.replace(day=1)
        ventas_mes_anterior = db.session.query(func.sum(Invoice.total_amount)).filter(
            Invoice.date >= start_of_previous_month,
            Invoice.date <= end_of_previous_month,
            Invoice.status == 'pagada'
        ).scalar() or 0
        
        # Totales generales (todas las facturas pagadas)
        total_sales_amount_pagadas = db.session.query(func.sum(Invoice.total_amount)).filter_by(status='pagada').scalar() or 0
        total_impuestos_recaudados = db.session.query(func.sum(Invoice.tax_amount)).filter_by(status='pagada').scalar() or 0
        total_descuentos_otorgados = db.session.query(func.sum(Invoice.discount_amount)).filter_by(status='pagada').scalar() or 0
        total_ventas_netas = db.session.query(
            func.sum(Invoice.subtotal - Invoice.discount_amount)
        ).filter_by(status='pagada').scalar() or 0
        
        # Notas de crédito
        total_notas_credito = CreditNote.query.count()
        monto_notas_credito = db.session.query(func.sum(CreditNote.total_amount)).scalar() or 0

        # --- 2. Gráficos Simples (Datos para JS) ---
        # Gráfico de barras de ventas por mes (últimos 6 meses)
        sales_by_month_data = []
        sales_by_month_labels = []
        for i in range(6): # 0 to 5 for current month and 5 previous months
            target_month = today.replace(day=1) - timedelta(days=30 * i) # Go back roughly i months
            target_month = target_month.replace(day=1) # Ensure it's the 1st of that month

            # Calculate start and end of the target month
            start_of_month = target_month
            # Get end of month by going to next month's 1st and subtracting 1 day
            end_of_month = (target_month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

            month_sales = db.session.query(func.sum(Invoice.total_amount)).filter(
                Invoice.date >= start_of_month,
                Invoice.date <= end_of_month,
                Invoice.status == 'pagada'
            ).scalar() or 0
            sales_by_month_data.insert(0, month_sales) # Insert at beginning to keep chronological order
            sales_by_month_labels.insert(0, start_of_month.strftime('%b %Y'))

        # Top 5 productos más vendidos (por cantidad)
        top_products = db.session.query(
            Product.name,
            func.sum(InvoiceItem.quantity).label('total_quantity')
        ).join(InvoiceItem).join(Invoice).filter(Invoice.status == 'pagada').group_by(Product.name).order_by(
            func.sum(InvoiceItem.quantity).desc()
        ).limit(5).all()
        top_products_labels = [p.name for p in top_products]
        top_products_data = [p.total_quantity for p in top_products]

        # Top 5 clientes que más compran (por monto)
        top_clients = db.session.query(
            Client.name,
            func.sum(Invoice.total_amount).label('total_spent')
        ).join(Invoice).filter(Invoice.status == 'pagada').group_by(Client.name).order_by(
            func.sum(Invoice.total_amount).desc()
        ).limit(5).all()
        top_clients_labels = [c.name for c in top_clients]
        top_clients_data = [c.total_spent for c in top_clients]

        # --- 3. Sección de Alertas ---
        # Facturas vencidas hace más de 30 días
        facturas_vencidas_30_dias = Invoice.query.filter(
            Invoice.due_date < (today - timedelta(days=30)),
            Invoice.status == 'no_pagada'
        ).count()

        # Stock bajo en productos específicos
        productos_stock_bajo_lista = Product.query.filter(Product.stock < umbral_stock_bajo).all()

        # Meta del mes (configurable desde config o .env)
        meta_mensual = float(getattr(Config, 'MONTHLY_SALES_TARGET', 10000.0))
        porcentaje_meta_alcanzada = (ventas_mes_actual / meta_mensual) * 100 if meta_mensual > 0 else 0
        alerta_meta_alcanzada = porcentaje_meta_alcanzada >= 85

        # --- 4. Indicadores de Rendimiento (KPIs) ---
        # Ticket Promedio
        total_invoices_pagadas = Invoice.query.filter_by(status='pagada').count()
        ticket_promedio = total_sales_amount_pagadas / total_invoices_pagadas if total_invoices_pagadas > 0 else 0

        # Tasa de Conversión (cotizaciones -> facturas)
        total_quotes_all = Quote.query.count()
        total_invoices_converted = Invoice.query.filter(Invoice.quote_id.isnot(None)).count()
        tasa_conversion = (total_invoices_converted / total_quotes_all) * 100 if total_quotes_all > 0 else 0

        # Días promedio de pago (portable - funciona con MySQL y SQLite)
        # Calcular diferencia en días usando Python si es necesario, o usar función de base de datos
        try:
            # Intentar con función de MySQL primero
            dias_promedio_pago_query = db.session.query(
                func.avg(func.datediff(Invoice.payment_date, Invoice.date))
            ).filter(Invoice.status == 'pagada', Invoice.payment_date.isnot(None)).scalar()
            dias_promedio_pago = dias_promedio_pago_query if dias_promedio_pago_query is not None else 0
        except Exception:
            # Fallback: calcular manualmente
            invoices_with_payment = Invoice.query.filter(
                Invoice.status == 'pagada',
                Invoice.payment_date.isnot(None)
            ).all()
            if invoices_with_payment:
                total_days = sum((inv.payment_date - inv.date.date()).days for inv in invoices_with_payment if inv.payment_date)
                dias_promedio_pago = total_days / len(invoices_with_payment) if invoices_with_payment else 0
            else:
                dias_promedio_pago = 0

        # Valor del inventario (suma de precio * stock)
        valor_inventario = db.session.query(
            func.sum(Product.price * Product.stock)
        ).scalar() or 0

        return render_template('dashboard.html', title='Dashboard',
                               # Existing metrics
                               total_clients=Client.query.count(),
                               total_products=Product.query.count(),
                               total_quotes=Quote.query.count(),
                               total_invoices=Invoice.query.count(),
                               total_sales_amount=total_sales_amount_pagadas,

                               # New Card Metrics
                               cotizaciones_pendientes=cotizaciones_pendientes,
                               facturas_vencidas=facturas_vencidas,
                               productos_stock_bajo_count=productos_stock_bajo_count,
                               ventas_mes_actual=ventas_mes_actual,
                               ventas_mes_anterior=ventas_mes_anterior,
                               ventas_netas_mes_actual=ventas_netas_mes_actual,
                               impuestos_mes_actual=impuestos_mes_actual,
                               descuentos_mes_actual=descuentos_mes_actual,

                               # Totales generales
                               total_impuestos_recaudados=total_impuestos_recaudados,
                               total_descuentos_otorgados=total_descuentos_otorgados,
                               total_ventas_netas=total_ventas_netas,
                               total_notas_credito=total_notas_credito,
                               monto_notas_credito=monto_notas_credito,
                               valor_inventario=valor_inventario,

                               # Chart Data
                               sales_by_month_labels=sales_by_month_labels,
                               sales_by_month_data=sales_by_month_data,
                               top_products_labels=top_products_labels,
                               top_products_data=top_products_data,
                               top_clients_labels=top_clients_labels,
                               top_clients_data=top_clients_data,

                               # Alerts
                               facturas_vencidas_30_dias=facturas_vencidas_30_dias,
                               productos_stock_bajo_lista=productos_stock_bajo_lista,
                               alerta_meta_alcanzada=alerta_meta_alcanzada,
                               porcentaje_meta_alcanzada=porcentaje_meta_alcanzada,
                               meta_mensual=meta_mensual,

                               # KPIs
                               ticket_promedio=ticket_promedio,
                               tasa_conversion=tasa_conversion,
                               dias_promedio_pago=dias_promedio_pago
                               )
    except Exception as e:
        current_app.logger.error(f"Error en dashboard: {e}")
        import traceback
        traceback.print_exc()
        flash('Error al cargar el dashboard. Por favor, intenta de nuevo.', 'danger')
        return redirect(url_for('main.index'))

@main.route('/download_pdf/<path:filename>')
@login_required
def download_pdf(filename):
    pdf_directory = os.path.join(current_app.instance_path, 'temp_pdfs')
    return send_from_directory(pdf_directory, filename)

def generate_reset_token():
    """Genera un token seguro para reset de contraseña"""
    return secrets.token_urlsafe(32)

def send_password_reset_email(user, token):
    """Envía email con enlace para resetear contraseña"""
    reset_url = url_for('main.reset_password', token=token, _external=True)
    
    msg = Message(
        subject='Recuperación de Contraseña - Sistema de Cotizaciones',
        recipients=[user.email],
        sender=current_app.config['MAIL_DEFAULT_SENDER']
    )
    
    msg.body = f"""Hola {user.name or user.username},

Has solicitado restablecer tu contraseña en el Sistema de Cotizaciones.

Para restablecer tu contraseña, haz clic en el siguiente enlace:
{reset_url}

Este enlace expirará en 1 hora.

Si no solicitaste este cambio, puedes ignorar este mensaje.

Saludos,
Equipo del Sistema de Cotizaciones
"""
    
    msg.html = f"""
    <html>
    <body>
        <h2>Recuperación de Contraseña</h2>
        <p>Hola <strong>{user.name or user.username}</strong>,</p>
        <p>Has solicitado restablecer tu contraseña en el Sistema de Cotizaciones.</p>
        <p>Para restablecer tu contraseña, haz clic en el siguiente enlace:</p>
        <p><a href="{reset_url}" style="background-color: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Restablecer Contraseña</a></p>
        <p>O copia y pega este enlace en tu navegador:</p>
        <p>{reset_url}</p>
        <p><strong>Este enlace expirará en 1 hora.</strong></p>
        <p>Si no solicitaste este cambio, puedes ignorar este mensaje.</p>
        <hr>
        <p style="color: #666; font-size: 12px;">Saludos,<br>Equipo del Sistema de Cotizaciones</p>
    </body>
    </html>
    """
    
    try:
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Error enviando email de reset: {e}")
        return False

@main.route('/request_password_reset', methods=['GET', 'POST'])
def request_password_reset():
    """Ruta para solicitar reset de contraseña"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RequestPasswordResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            # Invalidar tokens anteriores no usados del usuario
            PasswordResetToken.query.filter_by(
                user_id=user.id,
                used=False
            ).update({'used': True})
            db.session.commit()
            
            # Generar nuevo token
            token = generate_reset_token()
            expires_at = datetime.utcnow() + timedelta(hours=1)
            
            # Guardar token en BD
            reset_token = PasswordResetToken(
                user_id=user.id,
                token=token,
                expires_at=expires_at
            )
            db.session.add(reset_token)
            db.session.commit()
            
            # Enviar email
            if send_password_reset_email(user, token):
                flash('Se ha enviado un enlace de recuperación a tu correo electrónico. Por favor, revisa tu bandeja de entrada.', 'info')
            else:
                flash('Error al enviar el email. Por favor, intenta de nuevo más tarde.', 'danger')
        else:
            # Por seguridad, no revelar si el email existe o no
            flash('Si el email existe en nuestro sistema, recibirás un enlace de recuperación.', 'info')
        
        return redirect(url_for('main.login'))
    
    return render_template('reset_password_request.html', title='Recuperar Contraseña', form=form)

@main.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Ruta para resetear contraseña con token"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    # Buscar token válido
    reset_token = PasswordResetToken.query.filter_by(token=token, used=False).first()
    
    if not reset_token:
        flash('El enlace de recuperación es inválido o ya ha sido usado.', 'danger')
        return redirect(url_for('main.request_password_reset'))
    
    if datetime.utcnow() > reset_token.expires_at:
        flash('El enlace de recuperación ha expirado. Por favor, solicita uno nuevo.', 'danger')
        # Marcar como usado
        reset_token.used = True
        db.session.commit()
        return redirect(url_for('main.request_password_reset'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        # Actualizar contraseña
        user = reset_token.user
        user.set_password(form.password.data)
        
        # Marcar token como usado
        reset_token.used = True
        
        db.session.commit()
        
        flash('Tu contraseña ha sido restablecida exitosamente. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('main.login'))
    
    return render_template('reset_password.html', title='Restablecer Contraseña', form=form, token=token)