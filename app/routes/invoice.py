from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file, current_app, send_from_directory
import os
from flask_login import login_required, current_user
from app import db, mail
from flask_mail import Message
from app.models import Invoice, Client, Product, InvoiceItem, Payment, InventoryMovement
from app.forms import InvoiceForm, InvoiceItemForm, InvoiceFinancialUpdateForm
from app.numbering import next_invoice_number
from app.tenant import filter_by_company, ensure_company_id, get_company_default_tax_rate
import datetime
import weasyprint
import io
from pathlib import Path
import urllib.parse
import urllib.request
from sqlalchemy import or_, and_ # Import and_ as well
from app.whatsapp_utils import send_whatsapp_message # Import WhatsApp utility
from num2words import num2words # Import num2words
from config import Config
from itsdangerous import URLSafeTimedSerializer

invoices_bp = Blueprint('invoices', __name__, url_prefix='/invoices')

def generate_view_token(entity_id, entity_type='invoice', expires_in=3600):
    """Genera un token temporal para acceder a una vista"""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    data = f"{entity_type}:{entity_id}"
    return serializer.dumps(data, salt='view-token')

def validate_view_token(token, entity_id, entity_type='invoice', max_age=3600):
    """Valida un token temporal"""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        data = serializer.loads(token, salt='view-token', max_age=max_age)
        expected = f"{entity_type}:{entity_id}"
        return data == expected
    except:
        return False

def validate_id_format(id_value, blueprint_prefix='invoices'):
    """
    Valida que el ID en la URL no tenga ceros a la izquierda.
    Previene acceso no autorizado con URLs como '/invoices/09' -> 9
    """
    path_parts = request.path.strip('/').split('/')
    if len(path_parts) >= 2 and path_parts[0] == blueprint_prefix:
        url_id_str = path_parts[1]
        # Si el string original tiene ceros a la izquierda o no coincide con el ID convertido, es inválido
        if url_id_str != str(id_value) or (url_id_str.startswith('0') and len(url_id_str) > 1):
            from flask import abort
            abort(404)

def calculate_invoice_totals(invoice):
    """
    Calcula subtotal, discount_amount, tax_amount y total_amount de una factura basándose en sus ítems.
    Actualiza la factura en la base de datos.
    """
    # Calcular subtotal sumando todos los ítems
    subtotal = sum(item.total_price for item in invoice.items)
    
    # Calcular descuento
    discount_amount = 0.0
    if invoice.discount_type == 'percentage':
        discount_amount = subtotal * (invoice.discount_value / 100.0)
    elif invoice.discount_type == 'amount':
        discount_amount = min(invoice.discount_value, subtotal)  # No puede ser mayor que el subtotal
    
    # Monto después del descuento = valor neto (no se suma IVA en esta plataforma)
    amount_after_discount = subtotal - discount_amount

    # Sin IVA: total = valor neto (subtotal - descuento)
    tax_rate = 0.0
    tax_amount = 0.0
    total_amount = amount_after_discount
    
    # Actualizar la factura
    invoice.subtotal = subtotal
    invoice.discount_amount = discount_amount
    invoice.tax_rate = tax_rate
    invoice.tax_amount = tax_amount
    invoice.total_amount = total_amount
    
    return subtotal, discount_amount, tax_amount, total_amount

@invoices_bp.route('/')
@login_required
def list_invoices():
    q = (request.args.get('q') or request.args.get('search') or '').strip()
    date_from = (request.args.get('date_from') or request.args.get('start_date') or '').strip()
    date_to = (request.args.get('date_to') or request.args.get('end_date') or '').strip()
    status = (request.args.get('status') or '').strip()
    if status == 'all':
        status = ''

    base_query = filter_by_company(Invoice.query, Invoice)
    query = base_query.join(Client)
    filters = []
    if q:
        filters.append(or_(
            Invoice.invoice_number.ilike(f'%{q}%'),
            Client.name.ilike(f'%{q}%'),
            Client.document_number.ilike(f'%{q}%')
        ))
    if date_from:
        try:
            d = datetime.datetime.strptime(date_from, '%Y-%m-%d').date()
            filters.append(Invoice.date >= datetime.datetime.combine(d, datetime.datetime.min.time()))
        except ValueError:
            pass
    if date_to:
        try:
            d = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()
            filters.append(Invoice.date <= datetime.datetime.combine(d, datetime.datetime.max.time()))
        except ValueError:
            pass
    if status:
        filters.append(Invoice.status == status)
    if filters:
        query = query.filter(and_(*filters))
    invoices = query.order_by(Invoice.date.desc()).all()

    return render_template(
        'invoices/list.html',
        invoices=invoices,
        title='Facturas',
        filter_q=q,
        filter_date_from=date_from,
        filter_date_to=date_to,
        filter_status=status,
        filter_show_status=True,
        filter_status_options=[('', 'Todos'), ('borrador', 'Borrador'), ('no_pagada', 'No pagada'), ('parcial', 'Pago parcial'), ('pagada', 'Pagada'), ('vencida', 'Vencida'), ('anulada', 'Anulada')],
    )

@invoices_bp.route('/search', methods=['GET'])
@login_required
def search_invoices():
    """Endpoint JSON para búsqueda en tiempo real de facturas"""
    q = request.args.get('q', '').strip()
    
    if not q:
        return jsonify(invoices=[])
    
    base_query = filter_by_company(Invoice.query, Invoice)
    query = base_query.join(Client)
    
    # Buscar en número de factura, nombre del cliente y documento del cliente
    search_filter = or_(
        Invoice.invoice_number.ilike(f'%{q}%'),
        Client.name.ilike(f'%{q}%'),
        Client.document_number.ilike(f'%{q}%')
    )
    
    invoices = query.filter(search_filter).order_by(Invoice.date.desc()).limit(100).all()
    
    # Formatear resultados como JSON
    results = []
    for invoice in invoices:
        results.append({
            'id': invoice.id,
            'invoice_number': invoice.invoice_number,
            'date': invoice.date.strftime('%Y-%m-%d'),
            'client_name': invoice.client.name,
            'client_document_number': invoice.client.document_number or '',
            'status': invoice.status,
            'total_amount': float(invoice.total_amount) if invoice.total_amount else 0.0
        })
    
    return jsonify(invoices=results)

@invoices_bp.route('/new', methods=['GET', 'POST'])
@login_required
def add_invoice():
    form = InvoiceForm()
    client_query = filter_by_company(Client.query, Client)
    form.client_id.choices = [(c.id, c.name) for c in client_query.order_by('name').all()]

    # Generate next invoice number (único por empresa)
    generated_invoice_number = next_invoice_number(current_user.company_id)

    if form.validate_on_submit():
        # Usar IVA de la empresa (configuración)
        tax_rate = form.tax_rate.data if form.tax_rate.data is not None else get_company_default_tax_rate(current_user.company_id)
        
        # Obtener descuento del formulario
        discount_type = form.discount_type.data if form.discount_type.data else 'none'
        discount_value = form.discount_value.data if form.discount_value.data else 0.0
        
        today_inv = datetime.date.today()
        new_invoice = Invoice(
            client_id=form.client_id.data,
            invoice_number=generated_invoice_number,
            date=today_inv,
            due_date=today_inv + datetime.timedelta(days=30),
            company_id=current_user.company_id,
            subtotal=0.0,
            discount_type=discount_type,
            discount_value=discount_value,
            discount_amount=0.0,
            tax_rate=tax_rate,
            tax_amount=0.0,
            total_amount=0
        )
        db.session.add(new_invoice)
        db.session.commit()
        flash('Cabecera de la factura creada con éxito. Ahora puede añadir productos.', 'success')
        token = generate_view_token(new_invoice.id, 'invoice')
        return redirect(url_for('invoices.view_invoice', id=new_invoice.id, token=token))
    
    if not form.is_submitted():
        form.date.data = datetime.date.today()
        form.tax_rate.data = get_company_default_tax_rate(current_user.company_id)
        form.discount_type.data = 'none'
        form.discount_value.data = 0.0

    return render_template('invoices/form.html', form=form, title='Nueva Factura')

@invoices_bp.route('/<string:invalid_id>')
@login_required
def invalid_invoice_id(invalid_id):
    """Maneja IDs inválidos (strings) y devuelve 404 después de verificar autenticación"""
    from flask import abort
    abort(404)

@invoices_bp.route('/<int:id>', methods=['GET', 'POST'])
@invoices_bp.route('/<int:id>/<token>', methods=['GET', 'POST'])
@login_required
def view_invoice(id, token=None):
    # Si no hay token, devolver 404 (URLs antiguas no son válidas)
    if token is None:
        from flask import abort
        abort(404)
    
    # Validar formato del ID para prevenir acceso no autorizado
    validate_id_format(id, 'invoices')
    
    # Validar token
    if not validate_view_token(token, id, 'invoice'):
        from flask import abort
        abort(404)
    
    invoice = ensure_company_id(id, Invoice)
    # Generar token para usar en enlaces internos
    view_token = generate_view_token(id, 'invoice')
    item_form = InvoiceItemForm()
    financial_form = InvoiceFinancialUpdateForm(obj=invoice) # Instantiate new combined form

    # Distinguish between form submissions
    if request.method == 'POST':
        if 'add_item' in request.form and item_form.validate():
            product = ensure_company_id(item_form.product_id.data, Product)
            
            # Calcular stock disponible considerando items ya agregados en esta factura
            available_stock = product.stock
            for existing_item in invoice.items:
                if existing_item.product_id == product.id:
                    available_stock -= existing_item.quantity
            
            # Validar stock disponible
            if available_stock <= 0:
                flash(f'Stock agotado para {product.name}. No hay unidades disponibles.', 'danger')
            elif available_stock < item_form.quantity.data:
                flash(f'Stock insuficiente para {product.name}. Stock disponible: {available_stock}, Solicitado: {item_form.quantity.data}', 'danger')
            else:
                total_price = item_form.quantity.data * item_form.unit_price.data
                new_item = InvoiceItem(
                    invoice_id=invoice.id,
                    product_id=item_form.product_id.data,
                    quantity=item_form.quantity.data,
                    unit_price=item_form.unit_price.data,
                    total_price=total_price
                )
                db.session.add(new_item)
                previous_stock = product.stock
                product.stock -= item_form.quantity.data
                
                # Registrar movimiento de inventario
                movement = InventoryMovement(
                    product_id=product.id,
                    movement_type='sale',
                    quantity=-item_form.quantity.data,  # Negativo porque es una salida
                    previous_stock=previous_stock,
                    new_stock=product.stock,
                    reference_type='invoice',
                    reference_id=invoice.id,
                    user_id=current_user.id if current_user.is_authenticated else None,
                    notes=f'Ítem agregado a factura #{invoice.invoice_number}',
                    created_at=datetime.datetime.utcnow()
                )
                db.session.add(movement)
                
                # Recalcular totales con impuestos
                calculate_invoice_totals(invoice)
                db.session.commit()
                flash('Ítem añadido a la factura con éxito.', 'success')
            return redirect_to_view_invoice(invoice.id)

        # Handle combined financial form submission
        if 'update_financial' in request.form and financial_form.validate():
            # Update invoice status
            invoice.status = financial_form.status.data
            
            # Handle new payment record
            if financial_form.record_new_payment.data:
                new_payment = Payment(
                    invoice_id=invoice.id,
                    amount=financial_form.amount.data,
                    payment_date=datetime.date.today(),
                    method=financial_form.method.data
                )
                db.session.add(new_payment)
                flash(f'Pago registrado con éxito. Monto: {new_payment.amount}, Fecha: {new_payment.payment_date.strftime("%Y-%m-%d")}, Método: {new_payment.method}.', 'success')
            
            # Recalculate total paid amount and update invoice status based on payments
            # This logic is crucial and should run after any new payment is added
            total_paid_amount = sum(p.amount for p in invoice.payments)
            
            if total_paid_amount >= invoice.total_amount:
                invoice.status = 'pagada'
                # Set payment_date to the date of the last payment if fully paid by payments
                if invoice.payments:
                    invoice.payment_date = max(p.payment_date for p in invoice.payments)
            elif total_paid_amount > 0:
                invoice.status = 'parcial'
                invoice.payment_date = None # Clear payment date if it becomes partial
            else:
                invoice.status = 'no_pagada'
                invoice.payment_date = None # Clear payment date if no payments

            # If status was manually set to 'pagada' and no new payment was recorded, use form's payment_date
            if financial_form.status.data == 'pagada' and not financial_form.record_new_payment.data:
                invoice.payment_date = financial_form.payment_date.data
            
            db.session.commit()
            flash('Estado de la factura actualizado.', 'success')
            token = generate_view_token(invoice.id, 'invoice')
            return redirect(url_for('invoices.view_invoice', id=invoice.id, token=token))


    # Pre-fill forms for GET request
    if request.method == 'GET':
        financial_form.status.data = invoice.status
        # Pre-fill payment_date for the combined form
        # Use invoice's payment_date if available, otherwise today's date
        financial_form.payment_date.data = invoice.payment_date if invoice.payment_date else datetime.date.today()

    # Recalcular totales antes de mostrar (sin IVA: total = valor neto)
    calculate_invoice_totals(invoice)
    db.session.commit()

    # Conditionally populate choices for product_id for item_form
    if item_form.product_id.data:
        product = ensure_company_id(item_form.product_id.data, Product)
        if product:
            item_form.product_id.choices = [(product.id, f"{product.code} - {product.name}")]
    else:
        item_form.product_id.choices = []

    return render_template('invoices/view.html', invoice=invoice, item_form=item_form, financial_form=financial_form, title=f'Factura #{invoice.invoice_number}', view_token=view_token)

@invoices_bp.route('/<int:id>/pdf')
@login_required
def generate_invoice_pdf(id):
    invoice = ensure_company_id(id, Invoice)
    calculate_invoice_totals(invoice)
    db.session.commit()
    logo_disk_path = Path(os.path.join(current_app.root_path, 'img', '1.png'))
    logo_path = urllib.parse.urljoin('file:', urllib.request.pathname2url(str(logo_disk_path))) if logo_disk_path.exists() else None

    # Convert total amount to words
    amount_in_words = num2words(invoice.total_amount, lang='es').upper() + ' PESOS M/CTE.'

    html = render_template('invoices/pdf_template.html', invoice=invoice, logo_path=logo_path, amount_in_words=amount_in_words)
    
    # Define file path
    filename = f'fev_{invoice.invoice_number}_{datetime.date.today().strftime("%d%m%Y")}.pdf'
    pdf_path = os.path.join(current_app.instance_path, 'temp_pdfs', filename)

    # Ensure the directory exists
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    # Generate and save PDF
    weasyprint.HTML(string=html, base_url=request.base_url).write_pdf(pdf_path)

    # Return for download
    return send_from_directory(os.path.join(current_app.instance_path, 'temp_pdfs'), filename, as_attachment=True)

@invoices_bp.route('/<int:id>/send_email', methods=['GET', 'POST'])
@login_required
def send_invoice_email(id):
    invoice = ensure_company_id(id, Invoice)
    recipient_email = invoice.client.email

    if request.method == 'POST':
        html = render_template('invoices/pdf_template.html', invoice=invoice)
        pdf_content = weasyprint.HTML(string=html).write_pdf()

        msg = Message(
            subject=f'Factura #{invoice.invoice_number}',
            recipients=[recipient_email],
            body=f'''Estimado/a {invoice.client.name},

Adjunto encontrará la Factura #{invoice.invoice_number}.

Saludos,
Su Empresa''',
            html=render_template('emails/invoice_email.html', invoice=invoice)
        )
        msg.attach(
            f'factura_{invoice.invoice_number}.pdf',
            'application/pdf',
            pdf_content
        )
        try:
            mail.send(msg)
            flash('Correo enviado con éxito.', 'success')
        except Exception as e:
            flash(f'Error al enviar el correo: {e}', 'danger')
        token = generate_view_token(invoice.id, 'invoice')
        return redirect(url_for('invoices.view_invoice', id=invoice.id, token=token))

    return render_template('invoices/send_email_confirm.html', invoice=invoice, recipient_email=recipient_email, title=f'Enviar Factura #{invoice.invoice_number} por Email')

@invoices_bp.route('/<int:id>/send_whatsapp', methods=['POST'])
@login_required
def send_invoice_whatsapp(id):
    invoice = ensure_company_id(id, Invoice)
    if not invoice.client.whatsapp_number:
        flash('El cliente no tiene un número de WhatsApp registrado.', 'danger')
        token = generate_view_token(id, 'invoice')
        return redirect(url_for('invoices.view_invoice', id=id, token=token))

    # 1. Generate and save the PDF to get the filename
    filename = f'fev_{invoice.invoice_number}_{datetime.date.today().strftime("%d%m%Y")}.pdf'
    pdf_path = os.path.join(current_app.instance_path, 'temp_pdfs', filename)
    logo_disk_path = Path(os.path.join(current_app.root_path, 'img', '1.png'))
    logo_path = urllib.parse.urljoin('file:', urllib.request.pathname2url(str(logo_disk_path))) if logo_disk_path.exists() else None
    html = render_template('invoices/pdf_template.html', invoice=invoice, logo_path=logo_path)
    weasyprint.HTML(string=html, base_url=request.base_url).write_pdf(pdf_path)

    # 2. Create the public URL for the PDF
    pdf_url = url_for('main.download_pdf', filename=filename, _external=True)

    # 3. Format the message
    message = f"Estimado/a {invoice.client.name}, adjunto encontrará la factura #{invoice.invoice_number}. Puede descargarla aquí: {pdf_url}"

    # 4. Send the message
    success, response = send_whatsapp_message(invoice.client.whatsapp_number, message)

    if success:
        flash('Factura enviada por WhatsApp con éxito.', 'success')
    else:
        flash(f"Error al enviar por WhatsApp: {response.get('error', {}).get('message', 'Error desconocido')}", 'danger')

    token = generate_view_token(id, 'invoice')
    return redirect(url_for('invoices.view_invoice', id=id, token=token))