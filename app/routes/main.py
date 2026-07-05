from flask import render_template, flash, redirect, url_for, request, Blueprint, current_app, send_from_directory, session
from app import db, mail
from app.forms import LoginForm, RegistrationForm, RequestPasswordResetForm, ResetPasswordForm
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User, Client, Product, Quote, Invoice, InvoiceItem, CreditNote, PasswordResetToken, Company, CompanyConfig # Import new models
from app.tenant import filter_by_company, is_super_admin
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
        from app.route_tokens import url_with_token
        return redirect(url_with_token('main.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        # Username puede repetirse en distintas empresas; buscar todos y validar contraseña
        candidates = User.query.filter_by(username=form.username.data).all()
        valid_users = [u for u in candidates if u.check_password(form.password.data)]
        if not valid_users:
            flash('Usuario o contraseña inválidos', 'danger')
            return redirect(url_for('main.index'))
        # Solo usuarios activos
        valid_users = [u for u in valid_users if u.active]
        if not valid_users:
            flash('Tu cuenta ha sido desactivada. Contacta al administrador.', 'danger')
            return redirect(url_for('main.index'))
        # Un solo usuario: iniciar sesión directamente
        if len(valid_users) == 1:
            user = valid_users[0]
            login_user(user, remember=form.remember_me.data)
            from app.route_tokens import url_with_token
            next_page = request.args.get('next')
            if not next_page or urlsplit(next_page).netloc != '':
                next_page = url_with_token('main.dashboard')
            flash('¡Has iniciado sesión correctamente!', 'success')
            return redirect(next_page)
        # Varios usuarios con el mismo username: elegir empresa
        session['login_candidates'] = [
            {'user_id': u.id, 'company_id': u.company_id, 'company_name': u.company.name if u.company else 'Sin empresa'}
            for u in valid_users
        ]
        session['login_remember_me'] = form.remember_me.data
        return redirect(url_for('main.select_company'))
    return render_template('index.html', title='Inicio', form=form)

@main.route('/login/select_company', methods=['GET', 'POST'])
def select_company():
    """Cuando hay varios usuarios con el mismo username, elegir empresa para iniciar sesión."""
    if current_user.is_authenticated:
        from app.route_tokens import url_with_token
        return redirect(url_with_token('main.dashboard'))
    candidates = session.get('login_candidates')
    if not candidates:
        flash('Sesión de login expirada. Vuelve a iniciar sesión.', 'info')
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        company_id = request.form.get('company_id', type=int)
        if company_id is None:
            flash('Selecciona una empresa.', 'warning')
            return render_template('select_company.html', candidates=candidates, title='Elegir empresa')
        match = next((c for c in candidates if c['company_id'] == company_id), None)
        if not match:
            flash('Empresa no válida.', 'danger')
            return redirect(url_for('main.index'))
        user = User.query.get(match['user_id'])
        if not user or not user.active:
            session.pop('login_candidates', None)
            session.pop('login_remember_me', None)
            flash('Usuario no disponible.', 'danger')
            return redirect(url_for('main.index'))
        remember = session.pop('login_remember_me', False)
        session.pop('login_candidates', None)
        login_user(user, remember=remember)
        flash('¡Has iniciado sesión correctamente!', 'success')
        from app.route_tokens import url_with_token
        return redirect(url_with_token('main.dashboard'))
    return render_template('select_company.html', candidates=candidates, title='Elegir empresa')

@main.route('/favicon.ico')
def favicon():
    """Responde al favicon para evitar 404. Si existe static/favicon.ico se sirve; si no, 204."""
    import os
    static_folder = current_app.static_folder
    favicon_path = os.path.join(static_folder, 'favicon.ico') if static_folder else None
    if favicon_path and os.path.isfile(favicon_path):
        return send_from_directory(static_folder, 'favicon.ico')
    return '', 204

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
        # Opción B: Crear usuario sin empresa (requiere asignación por super-admin)
        # Necesitamos una empresa temporal o hacer company_id nullable
        # Por ahora, creamos una empresa temporal que será asignada por super-admin
        # O mejor: deshabilitar registro público y solo permitir creación por super-admin
        flash('El registro público está deshabilitado. Por favor, contacta al administrador del sistema.', 'info')
        return redirect(url_for('main.index'))
        
        # Código anterior comentado - solo super-admins pueden crear empresas ahora
        # # Crear nueva empresa para el usuario
        # company = Company(
        #     name=form.name.data or form.username.data,
        #     active=True
        # )
        # db.session.add(company)
        # db.session.flush()
        # 
        # # Crear configuración por defecto para la empresa
        # company_config = CompanyConfig(
        #     company_id=company.id,
        #     default_tax_rate=19.0,
        #     monthly_sales_target=10000.0,
        #     quote_number_prefix='COT',
        #     invoice_number_prefix='FAC',
        #     credit_note_number_prefix='NC'
        # )
        # db.session.add(company_config)
        # 
        # # Crear usuario y asignarlo a la empresa
        # user = User(
        #     name=form.name.data, 
        #     username=form.username.data, 
        #     email=form.email.data,
        #     company_id=company.id,
        #     role='admin',
        #     active=True
        # )
        # user.set_password(form.password.data)
        # db.session.add(user)
        # db.session.flush()
        # 
        # company.created_by = user.id
        # db.session.commit()
        # flash('¡Felicidades, ahora eres un usuario registrado!', 'success')
        # return redirect(url_for('main.login'))
    return render_template('register.html', title='Registro', form=form)

@main.route('/dashboard')
@login_required
@role_required(['user', 'admin', 'super_admin', 'bodega_principal', 'despachador'])
def dashboard():
    # Super-admin solo administra empresas y usuarios; no ve datos de negocio
    if is_super_admin():
        from app.route_tokens import url_with_token
        return redirect(url_with_token('admin.list_companies'))
    try:
        today = date.today()

        # --- 1. Métricas Adicionales (nuevas tarjetas) ---
        # Cotizaciones Pendientes (status='pendiente') - filtradas por empresa
        quote_base = filter_by_company(Quote.query, Quote)
        cotizaciones_pendientes = quote_base.filter_by(status='pendiente').count()

        # Facturas Vencidas (due_date < today and status='no_pagada') - filtradas por empresa
        invoice_base = filter_by_company(Invoice.query, Invoice)
        facturas_vencidas = invoice_base.filter(
            Invoice.due_date < today,
            Invoice.status == 'no_pagada'
        ).count()

        # Productos con Stock Bajo (stock < 5) - filtrados por empresa
        umbral_stock_bajo = 5
        product_base = filter_by_company(Product.query, Product)
        productos_stock_bajo_count = product_base.filter(Product.stock < umbral_stock_bajo).count()

        # Ventas del Mes Actual vs Anterior - Separar subtotal, impuestos y descuentos
        start_of_current_month = today.replace(day=1)
        
        # Ventas totales (con impuestos) - filtradas por empresa
        ventas_mes_actual = db.session.query(func.sum(Invoice.total_amount)).filter(
            Invoice.company_id == current_user.company_id,
            Invoice.date >= start_of_current_month,
            Invoice.status == 'pagada'
        ).scalar() or 0
        
        # Subtotal (sin impuestos, después de descuentos) - filtrado por empresa (o todas si es super_admin)
        ventas_netas_query = db.session.query(
            func.sum(Invoice.subtotal - Invoice.discount_amount)
        ).filter(
            Invoice.date >= start_of_current_month,
            Invoice.status == 'pagada'
        )
        if not is_super_admin():
            ventas_netas_query = ventas_netas_query.filter(Invoice.company_id == current_user.company_id)
        ventas_netas_mes_actual = ventas_netas_query.scalar() or 0
        
        # Impuestos recaudados del mes - filtrado por empresa (o todas si es super_admin)
        impuestos_query = db.session.query(func.sum(Invoice.tax_amount)).filter(
            Invoice.date >= start_of_current_month,
            Invoice.status == 'pagada'
        )
        if not is_super_admin():
            impuestos_query = impuestos_query.filter(Invoice.company_id == current_user.company_id)
        impuestos_mes_actual = impuestos_query.scalar() or 0
        
        # Descuentos otorgados del mes - filtrado por empresa (o todas si es super_admin)
        descuentos_query = db.session.query(func.sum(Invoice.discount_amount)).filter(
            Invoice.date >= start_of_current_month,
            Invoice.status == 'pagada'
        )
        if not is_super_admin():
            descuentos_query = descuentos_query.filter(Invoice.company_id == current_user.company_id)
        descuentos_mes_actual = descuentos_query.scalar() or 0

        # Sales for previous month - filtrado por empresa (o todas si es super_admin)
        end_of_previous_month = start_of_current_month - timedelta(days=1)
        start_of_previous_month = end_of_previous_month.replace(day=1)
        ventas_anterior_query = db.session.query(func.sum(Invoice.total_amount)).filter(
            Invoice.date >= start_of_previous_month,
            Invoice.date <= end_of_previous_month,
            Invoice.status == 'pagada'
        )
        if not is_super_admin():
            ventas_anterior_query = ventas_anterior_query.filter(Invoice.company_id == current_user.company_id)
        ventas_mes_anterior = ventas_anterior_query.scalar() or 0
        
        # Totales generales (todas las facturas pagadas) - filtrado por empresa (o todas si es super_admin)
        total_sales_query = db.session.query(func.sum(Invoice.total_amount)).filter(
            Invoice.status == 'pagada'
        )
        total_impuestos_query = db.session.query(func.sum(Invoice.tax_amount)).filter(
            Invoice.status == 'pagada'
        )
        total_descuentos_query = db.session.query(func.sum(Invoice.discount_amount)).filter(
            Invoice.status == 'pagada'
        )
        total_ventas_netas_query = db.session.query(
            func.sum(Invoice.subtotal - Invoice.discount_amount)
        ).filter(
            Invoice.status == 'pagada'
        )
        if not is_super_admin():
            total_sales_query = total_sales_query.filter(Invoice.company_id == current_user.company_id)
            total_impuestos_query = total_impuestos_query.filter(Invoice.company_id == current_user.company_id)
            total_descuentos_query = total_descuentos_query.filter(Invoice.company_id == current_user.company_id)
            total_ventas_netas_query = total_ventas_netas_query.filter(Invoice.company_id == current_user.company_id)
        total_sales_amount_pagadas = total_sales_query.scalar() or 0
        total_impuestos_recaudados = total_impuestos_query.scalar() or 0
        total_descuentos_otorgados = total_descuentos_query.scalar() or 0
        total_ventas_netas = total_ventas_netas_query.scalar() or 0
        
        # Notas de crédito - filtradas por empresa (o todas si es super_admin)
        credit_note_base = filter_by_company(CreditNote.query, CreditNote)
        total_notas_credito = credit_note_base.count()
        monto_notas_query = db.session.query(func.sum(CreditNote.total_amount))
        if not is_super_admin():
            monto_notas_query = monto_notas_query.filter(CreditNote.company_id == current_user.company_id)
        monto_notas_credito = monto_notas_query.scalar() or 0

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

            month_sales_query = db.session.query(func.sum(Invoice.total_amount)).filter(
                Invoice.date >= start_of_month,
                Invoice.date <= end_of_month,
                Invoice.status == 'pagada'
            )
            if not is_super_admin():
                month_sales_query = month_sales_query.filter(Invoice.company_id == current_user.company_id)
            month_sales = month_sales_query.scalar() or 0
            sales_by_month_data.insert(0, month_sales) # Insert at beginning to keep chronological order
            sales_by_month_labels.insert(0, start_of_month.strftime('%b %Y'))

        # Top 5 productos más vendidos (por cantidad) - filtrado por empresa (o todas si es super_admin)
        top_products_query = db.session.query(
            Product.name,
            func.sum(InvoiceItem.quantity).label('total_quantity')
        ).join(InvoiceItem).join(Invoice).filter(
            Invoice.status == 'pagada'
        )
        if not is_super_admin():
            top_products_query = top_products_query.filter(Invoice.company_id == current_user.company_id)
        top_products = top_products_query.group_by(Product.name).order_by(
            func.sum(InvoiceItem.quantity).desc()
        ).limit(5).all()
        top_products_labels = [p.name for p in top_products]
        top_products_data = [p.total_quantity for p in top_products]

        # Top 5 clientes que más compran (por monto) - filtrado por empresa (o todas si es super_admin)
        top_clients_query = db.session.query(
            Client.name,
            func.sum(Invoice.total_amount).label('total_spent')
        ).join(Invoice).filter(
            Invoice.status == 'pagada'
        )
        if not is_super_admin():
            top_clients_query = top_clients_query.filter(Invoice.company_id == current_user.company_id)
        top_clients = top_clients_query.group_by(Client.name).order_by(
            func.sum(Invoice.total_amount).desc()
        ).limit(5).all()
        top_clients_labels = [c.name for c in top_clients]
        top_clients_data = [c.total_spent for c in top_clients]

        # --- 3. Sección de Alertas ---
        # Facturas vencidas hace más de 30 días - filtradas por empresa
        facturas_vencidas_30_dias = invoice_base.filter(
            Invoice.due_date < (today - timedelta(days=30)),
            Invoice.status == 'no_pagada'
        ).count()

        # Stock bajo en productos específicos - filtrados por empresa
        productos_stock_bajo_lista = product_base.filter(Product.stock < umbral_stock_bajo).all()

        # Meta del mes (configurable desde config o .env)
        meta_mensual = float(getattr(Config, 'MONTHLY_SALES_TARGET', 10000.0))
        porcentaje_meta_alcanzada = (ventas_mes_actual / meta_mensual) * 100 if meta_mensual > 0 else 0
        alerta_meta_alcanzada = porcentaje_meta_alcanzada >= 85

        # --- 4. Indicadores de Rendimiento (KPIs) ---
        # Ticket Promedio - filtrado por empresa
        total_invoices_pagadas = invoice_base.filter_by(status='pagada').count()
        ticket_promedio = total_sales_amount_pagadas / total_invoices_pagadas if total_invoices_pagadas > 0 else 0

        # Tasa de Conversión (cotizaciones -> facturas) - filtrado por empresa
        total_quotes_all = quote_base.count()
        total_invoices_converted = invoice_base.filter(Invoice.quote_id.isnot(None)).count()
        tasa_conversion = (total_invoices_converted / total_quotes_all) * 100 if total_quotes_all > 0 else 0

        # Días promedio de pago (portable - funciona con MySQL y SQLite)
        # Calcular diferencia en días usando Python si es necesario, o usar función de base de datos
        try:
            # Intentar con función de MySQL primero
            dias_promedio_pago_query = db.session.query(
                func.avg(func.datediff(Invoice.payment_date, Invoice.date))
            ).filter(
                Invoice.status == 'pagada',
                Invoice.payment_date.isnot(None)
            )
            if not is_super_admin():
                dias_promedio_pago_query = dias_promedio_pago_query.filter(Invoice.company_id == current_user.company_id)
            dias_promedio_pago_query = dias_promedio_pago_query.scalar()
            dias_promedio_pago = dias_promedio_pago_query if dias_promedio_pago_query is not None else 0
        except Exception:
            # Fallback: calcular manualmente
            invoices_with_payment = invoice_base.filter(
                Invoice.status == 'pagada',
                Invoice.payment_date.isnot(None)
            ).all()
            if invoices_with_payment:
                total_days = sum((inv.payment_date - inv.date.date()).days for inv in invoices_with_payment if inv.payment_date)
                dias_promedio_pago = total_days / len(invoices_with_payment) if invoices_with_payment else 0
            else:
                dias_promedio_pago = 0

        # Valor del inventario (suma de precio * stock) - filtrado por empresa (o todas si es super_admin)
        valor_inventario_query = db.session.query(
            func.sum(Product.price * Product.stock)
        )
        if not is_super_admin():
            valor_inventario_query = valor_inventario_query.filter(Product.company_id == current_user.company_id)
        valor_inventario = valor_inventario_query.scalar() or 0

        # Obtener contadores filtrados por empresa
        client_base = filter_by_company(Client.query, Client)
        
        return render_template('dashboard.html', title='Dashboard',
                               # Existing metrics - filtradas por empresa
                               total_clients=client_base.count(),
                               total_products=product_base.count(),
                               total_quotes=quote_base.count(),
                               total_invoices=invoice_base.count(),
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
        user = User.query.filter_by(
            username=form.username.data.strip(),
            email=form.email.data.strip(),
        ).first()
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