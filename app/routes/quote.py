from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file, current_app, send_from_directory
import os
from flask_login import login_required, current_user
from app import db, mail # Import mail
from app.models import Quote, Client, Product, QuoteItem, Invoice, InvoiceItem, InventoryMovement # Import Invoice and InvoiceItem
from app.forms import QuoteForm, QuoteItemForm, UpdateQuoteStatusForm, QuoteItemEditForm # Import QuoteItemEditForm
from app.tenant import filter_by_company, ensure_company_id, get_company_default_tax_rate, resolve_entity_company_id, get_current_company_id
from app.decorators import role_required, log_audit
from app.numbering import next_invoice_number
from sqlalchemy.exc import IntegrityError
from flask_mail import Message # Import Message
import datetime
import weasyprint
import io
from pathlib import Path
import urllib.parse
import urllib.request
from app.whatsapp_utils import send_whatsapp_message # Import WhatsApp utility
from num2words import num2words # Import num2words
from sqlalchemy import or_, and_ # Import and_ as well
from config import Config
from itsdangerous import URLSafeTimedSerializer

quotes_bp = Blueprint('quotes', __name__, url_prefix='/quotes')

def generate_view_token(entity_id, entity_type='quote', expires_in=3600):
    """Genera un token temporal para acceder a una vista"""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    data = f"{entity_type}:{entity_id}"
    return serializer.dumps(data, salt='view-token')

def validate_view_token(token, entity_id, entity_type='quote', max_age=3600):
    """Valida un token temporal"""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        data = serializer.loads(token, salt='view-token', max_age=max_age)
        expected = f"{entity_type}:{entity_id}"
        return data == expected
    except:
        return False

def redirect_to_view_quote(quote_id):
    """Helper para redirigir a view_quote con token"""
    token = generate_view_token(quote_id, 'quote')
    return redirect(url_for('quotes.view_quote', id=quote_id, token=token))

def validate_id_format(id_value, blueprint_prefix='quotes'):
    """
    Valida que el ID en la URL no tenga ceros a la izquierda.
    Previene acceso no autorizado con URLs como '/quotes/09' -> 9
    """
    path_parts = request.path.strip('/').split('/')
    if len(path_parts) >= 2 and path_parts[0] == blueprint_prefix:
        url_id_str = path_parts[1]
        # Si el string original tiene ceros a la izquierda o no coincide con el ID convertido, es inválido
        if url_id_str != str(id_value) or (url_id_str.startswith('0') and len(url_id_str) > 1):
            from flask import abort
            abort(404)

def calculate_quote_totals(quote):
    """
    Calcula subtotal, discount_amount, tax_amount y total_amount de una cotización basándose en sus ítems.
    Actualiza la cotización en la base de datos.
    """
    # Calcular subtotal sumando todos los ítems
    subtotal = sum(item.total_price for item in quote.items)
    
    # Calcular descuento
    discount_amount = 0.0
    if quote.discount_type == 'percentage':
        discount_amount = subtotal * (quote.discount_value / 100.0)
    elif quote.discount_type == 'amount':
        discount_amount = min(quote.discount_value, subtotal)  # No puede ser mayor que el subtotal
    
    # Monto después del descuento = valor neto (no se suma IVA en esta plataforma)
    amount_after_discount = subtotal - discount_amount
    
    # Sin IVA: total = valor neto (subtotal - descuento)
    tax_rate = 0.0
    tax_amount = 0.0
    total_amount = amount_after_discount

    # Actualizar la cotización
    quote.subtotal = subtotal
    quote.discount_amount = discount_amount
    quote.tax_rate = tax_rate
    quote.tax_amount = tax_amount
    quote.total_amount = total_amount
    
    return subtotal, discount_amount, tax_amount, total_amount

@quotes_bp.route('/')
@login_required
def list_quotes():
    # Parámetros estándar: q, date_from, date_to, status (también acepta search, start_date, end_date)
    q = (request.args.get('q') or request.args.get('search') or '').strip()
    date_from = (request.args.get('date_from') or request.args.get('start_date') or '').strip()
    date_to = (request.args.get('date_to') or request.args.get('end_date') or '').strip()
    status = (request.args.get('status') or '').strip()
    if status == 'all':
        status = ''

    base_query = filter_by_company(Quote.query, Quote)
    query = base_query.join(Client)
    filters = []

    if q:
        filters.append(or_(
            Quote.quote_number.ilike(f'%{q}%'),
            Client.name.ilike(f'%{q}%'),
            Client.document_number.ilike(f'%{q}%')
        ))
    if date_from:
        try:
            d = datetime.datetime.strptime(date_from, '%Y-%m-%d').date()
            filters.append(Quote.date >= datetime.datetime.combine(d, datetime.datetime.min.time()))
        except ValueError:
            pass
    if date_to:
        try:
            d = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()
            filters.append(Quote.date <= datetime.datetime.combine(d, datetime.datetime.max.time()))
        except ValueError:
            pass
    if status:
        filters.append(Quote.status == status)

    if filters:
        query = query.filter(and_(*filters))
    quotes = query.order_by(Quote.date.desc()).all()

    return render_template(
        'quotes/list.html',
        quotes=quotes,
        title='Cotizaciones',
        filter_q=q,
        filter_date_from=date_from,
        filter_date_to=date_to,
        filter_status=status,
        filter_show_status=True,
        filter_status_options=[('', 'Todos'), ('pendiente', 'Pendiente'), ('aceptada', 'Aceptada'), ('rechazada', 'Rechazada'), ('vencida', 'Vencida'), ('facturada', 'Facturada')],
    )

@quotes_bp.route('/search', methods=['GET'])
@login_required
def search_quotes():
    """Endpoint JSON para búsqueda en tiempo real de cotizaciones"""
    q = request.args.get('q', '').strip()
    
    if not q:
        return jsonify(quotes=[])
    
    base_query = filter_by_company(Quote.query, Quote)
    query = base_query.join(Client)
    
    # Buscar en número de cotización, nombre del cliente y documento del cliente
    search_filter = or_(
        Quote.quote_number.ilike(f'%{q}%'),
        Client.name.ilike(f'%{q}%'),
        Client.document_number.ilike(f'%{q}%')
    )
    
    quotes = query.filter(search_filter).order_by(Quote.date.desc()).limit(100).all()
    
    # Formatear resultados como JSON
    results = []
    for quote in quotes:
        results.append({
            'id': quote.id,
            'quote_number': quote.quote_number,
            'date': quote.date.strftime('%Y-%m-%d'),
            'client_name': quote.client.name,
            'client_document_number': quote.client.document_number or '',
            'status': quote.status,
            'total_amount': float(quote.total_amount) if quote.total_amount else 0.0,
            'token': generate_view_token(quote.id, 'quote')
        })
    
    return jsonify(quotes=results)

@quotes_bp.route('/new', methods=['GET', 'POST'])
@login_required
def add_quote():
    form = QuoteForm()
    # Populate client choices (filtrados por empresa)
    client_query = filter_by_company(Client.query, Client)
    form.client_id.choices = [(c.id, c.name) for c in client_query.order_by('name').all()]
    
    # Generate next quote number (único por empresa)
    base_quote_query = filter_by_company(Quote.query, Quote)
    last_quote = base_quote_query.order_by(Quote.id.desc()).first()
    if last_quote and last_quote.quote_number.isdigit(): # Check if it's purely numeric
        next_number = int(last_quote.quote_number) + 1
    else:
        next_number = 1
    
    # Ensure the number starts from at least 118
    if next_number < 118:
        next_number = 118
        
    generated_quote_number = str(next_number).zfill(4) # Format as 0001, 0002 etc.

    if form.validate_on_submit():
        # Usar IVA de la empresa (configuración)
        tax_rate = form.tax_rate.data if form.tax_rate.data is not None else get_company_default_tax_rate(current_user.company_id)
        
        # Obtener descuento del formulario
        discount_type = form.discount_type.data if form.discount_type.data else 'none'
        discount_value = form.discount_value.data if form.discount_value.data else 0.0
        
        # Create the new Quote object
        new_quote = Quote(
            client_id=form.client_id.data,
            quote_number=generated_quote_number, # Use the generated number
            date=datetime.date.today(),
            company_id=current_user.company_id,
            subtotal=0.0,
            discount_type=discount_type,
            discount_value=discount_value,
            discount_amount=0.0,
            tax_rate=tax_rate,
            tax_amount=0.0,
            total_amount=0  # Initialize total amount to 0
        )
        db.session.add(new_quote)
        db.session.commit()
        flash('Cabecera de la cotización creada con éxito. Ahora puede añadir productos.', 'success')
        # Redirect to a (future) page to view/edit the quote and add items
        return redirect_to_view_quote(new_quote.id) 
        
    # Pre-fill form with sensible defaults on GET request (IVA desde configuración de la empresa)
    if not form.is_submitted():
        form.date.data = datetime.date.today()
        form.tax_rate.data = get_company_default_tax_rate(current_user.company_id)
        form.discount_type.data = 'none'
        form.discount_value.data = 0.0
        # Pre-fill the quote_number field with the generated number
        
        
    return render_template('quotes/form.html', form=form, title='Nueva Cotización')

@quotes_bp.route('/<string:invalid_id>')
@login_required
def invalid_quote_id(invalid_id):
    """Maneja IDs inválidos (strings) y devuelve 404 después de verificar autenticación"""
    from flask import abort
    abort(404)

@quotes_bp.route('/<int:id>', methods=['GET', 'POST'])
@quotes_bp.route('/<int:id>/<token>', methods=['GET', 'POST'])
@login_required
def view_quote(id, token=None):
    # Si no hay token, devolver 404 (URLs antiguas no son válidas)
    if token is None:
        from flask import abort
        abort(404)
    
    # Validar formato del ID para prevenir acceso no autorizado
    validate_id_format(id, 'quotes')
    
    # Validar token
    if not validate_view_token(token, id, 'quote'):
        from flask import abort
        abort(404)
    
    quote = ensure_company_id(id, Quote)
    # Generar token para usar en enlaces internos
    view_token = generate_view_token(id, 'quote')
    item_form = QuoteItemForm()
    status_form = UpdateQuoteStatusForm(obj=quote) # New form instance

    # Populate choices for product_id for item_form (always, for GET and POST)
    product_query = filter_by_company(Product.query, Product)
    item_form.product_id.choices = [(None, 'Seleccione un producto')] + [(p.id, f"{p.code} - {p.name}") for p in product_query.order_by('name').all()]

    # If product_id is already set (e.g., after a failed submission), pre-fill unit_price
    if item_form.product_id.data:
        selected_product = ensure_company_id(item_form.product_id.data, Product)
        if selected_product:
            item_form.unit_price.data = selected_product.price

    # Distinguish between form submissions
    if request.method == 'POST':
        if quote.status == 'facturada':
            flash('Esta cotización ya ha sido facturada y no puede ser modificada.', 'warning')
            return redirect_to_view_quote(quote.id)

        if 'update_status' in request.form and status_form.validate():
            quote.status = status_form.status.data
            db.session.commit()
            flash('Estado de la cotización actualizado.', 'success')
            return redirect_to_view_quote(quote.id)

        if 'add_item' in request.form and item_form.validate():
            product = ensure_company_id(item_form.product_id.data, Product)
            
            # Calcular stock disponible considerando items ya agregados en esta cotización
            available_stock = product.stock
            for existing_item in quote.items:
                if existing_item.product_id == product.id:
                    available_stock -= existing_item.quantity
            
            # Validar stock disponible
            if available_stock <= 0:
                flash(f'Stock agotado para {product.name}. No hay unidades disponibles.', 'danger')
            elif available_stock < item_form.quantity.data:
                flash(f'Stock insuficiente para {product.name}. Stock disponible: {available_stock}, Solicitado: {item_form.quantity.data}', 'danger')
            else:
                total_price = item_form.quantity.data * item_form.unit_price.data
                new_item = QuoteItem(
                    quote_id=quote.id,
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
                    reference_type='quote',
                    reference_id=quote.id,
                    user_id=current_user.id if current_user.is_authenticated else None,
                    notes=f'Ítem agregado a cotización #{quote.quote_number}',
                    created_at=datetime.datetime.utcnow()
                )
                db.session.add(movement)
                
                # Recalcular totales con impuestos
                calculate_quote_totals(quote)
                db.session.commit()
                flash('Ítem añadido a la cotización con éxito.', 'success')
            return redirect_to_view_quote(quote.id)

    # Pre-fill status form for GET request
    if request.method == 'GET':
        status_form.status.data = quote.status

    # Recalcular totales siempre antes de mostrar (subtotal, descuento, IVA, total) para que coincidan con los ítems
    calculate_quote_totals(quote)
    db.session.commit()

    # Conditionally populate choices for product_id for item_form
    product_query = filter_by_company(Product.query, Product)
    item_form.product_id.choices = [(None, 'Seleccione un producto')] + [(p.id, f"{p.code} - {p.name}") for p in product_query.order_by('name').all()]

    return render_template('quotes/view.html', quote=quote, item_form=item_form, status_form=status_form, title=f'Cotización #{quote.quote_number}', csrf_token=status_form.csrf_token._value(), view_token=view_token)

@quotes_bp.route('/<int:quote_id>/items/<int:item_id>/edit', methods=['POST'])
@login_required
@role_required(['admin', 'super_admin'])
def edit_quote_item(quote_id, item_id):
    quote = ensure_company_id(quote_id, Quote)
    if quote.status == 'facturada':
        return jsonify({'success': False, 'message': 'Esta cotización ya ha sido facturada y no puede ser modificada.'})

    item = QuoteItem.query.get_or_404(item_id)
    if item.quote_id != quote.id:
        return jsonify({'success': False, 'message': 'Ítem no encontrado en esta cotización.'})

    form = QuoteItemEditForm()
    if form.validate_on_submit():
        old_quantity = item.quantity
        old_total_price = item.total_price

        # Validar stock antes de actualizar
        product = ensure_company_id(item.product_id, Product)
        
        # Calcular stock disponible considerando otros items en la cotización
        available_stock = product.stock
        for existing_item in quote.items:
            if existing_item.product_id == product.id and existing_item.id != item.id:
                available_stock -= existing_item.quantity
        
        # Verificar si la nueva cantidad excede el stock disponible
        if form.quantity.data > available_stock:
            return jsonify({
                'success': False, 
                'message': f'Stock insuficiente. Disponible: {available_stock}, Solicitado: {form.quantity.data}'
            })
        
        item.quantity = form.quantity.data
        item.unit_price = form.unit_price.data
        item.total_price = item.quantity * item.unit_price

        # Update product stock
        previous_stock = product.stock
        quantity_change = old_quantity - item.quantity  # Cambio neto (positivo si se reduce cantidad)
        new_stock = product.stock + quantity_change
        
        # Validar que el stock no quede negativo
        if new_stock < 0:
            return jsonify({
                'success': False, 
                'message': f'No se puede reducir la cantidad. El stock quedaría negativo: {new_stock}'
            })
        
        product.stock = new_stock
        
        # Registrar movimiento de inventario si hay cambio
        if quantity_change != 0:
            movement = InventoryMovement(
                product_id=product.id,
                movement_type='sale',
                quantity=-quantity_change,  # Negativo si se reduce cantidad (entrada de stock)
                previous_stock=previous_stock,
                new_stock=product.stock,
                reference_type='quote',
                reference_id=quote.id,
                user_id=current_user.id if current_user.is_authenticated else None,
                notes=f'Ítem editado en cotización #{quote.quote_number}',
                created_at=datetime.datetime.utcnow()
            )
            db.session.add(movement)

        # Recalcular totales con impuestos
        calculate_quote_totals(quote)

        db.session.commit()
        return jsonify({'success': True, 'message': 'Ítem actualizado con éxito.'})
    else:
        error_messages = []
        for field, errors in form.errors.items():
            for error in errors:
                error_messages.append(f'{field}: {error}')
        return jsonify({'success': False, 'message': 'Error de validación', 'errors': error_messages})

@quotes_bp.route('/<int:quote_id>/items/<int:item_id>/delete', methods=['POST'])
@login_required
@role_required(['user', 'admin', 'super_admin'])
def delete_quote_item(quote_id, item_id):
    quote = ensure_company_id(quote_id, Quote)
    if quote.status == 'facturada': # Prevent deletion if quote is invoiced
        flash('Esta cotización ya ha sido facturada y no se pueden eliminar ítems.', 'danger')
        return redirect_to_view_quote(quote.id)

    item = QuoteItem.query.get_or_404(item_id)
    if item.quote_id != quote.id: # Ensure item belongs to the correct quote
        flash('Ítem no encontrado en esta cotización.', 'danger')
        return redirect_to_view_quote(quote.id)

    # Update product stock before deleting item
    product = ensure_company_id(item.product_id, Product)
    previous_stock = product.stock
    product.stock += item.quantity # Return stock
    
    # Registrar movimiento de inventario
    movement = InventoryMovement(
        product_id=product.id,
        movement_type='return',
        quantity=item.quantity,  # Positivo porque es una entrada (devolución)
        previous_stock=previous_stock,
        new_stock=product.stock,
        reference_type='quote',
        reference_id=quote.id,
        user_id=current_user.id if current_user.is_authenticated else None,
        notes=f'Ítem eliminado de cotización #{quote.quote_number}',
        created_at=datetime.datetime.utcnow()
    )
    db.session.add(movement)

    db.session.delete(item)
    
    # Recalcular totales con impuestos
    calculate_quote_totals(quote)
    
    db.session.commit()
    flash('Ítem eliminado de la cotización con éxito.', 'success')
    return redirect_to_view_quote(quote.id)

@quotes_bp.route('/get_product_price/<int:product_id>')
@login_required
def get_product_price(product_id):
    product = ensure_company_id(product_id, Product)
    return jsonify({'price': product.price})

@quotes_bp.route('/<int:id>/pdf')
@quotes_bp.route('/<int:id>/<token>/pdf')
@login_required
def generate_quote_pdf(id, token=None):
    # Si hay token, validarlo
    if token and not validate_view_token(token, id, 'quote'):
        from flask import abort
        abort(404)
    # Si no hay token, devolver 404 (URLs antiguas no son válidas)
    elif token is None:
        from flask import abort
        abort(404)
    
    quote = ensure_company_id(id, Quote)
    calculate_quote_totals(quote)
    db.session.commit()

    logo_disk_path = Path(os.path.join(current_app.root_path, 'img', '1.png'))
    logo_path = urllib.parse.urljoin('file:', urllib.request.pathname2url(str(logo_disk_path))) if logo_disk_path.exists() else None

    # Valor neto para el PDF (sin IVA): subtotal - descuento; se pasa explícitamente para que el PDF nunca muestre IVA
    net_total = float(quote.subtotal) - float(quote.discount_amount or 0)
    amount_in_words = num2words(net_total, lang='es').upper() + ' PESOS M/CTE.'

    html = render_template('quotes/pdf_template.html', quote=quote, logo_path=logo_path, amount_in_words=amount_in_words, total_neto=net_total)
    
    # Define file path
    filename = f'cotizacion_{quote.quote_number}_{datetime.date.today().strftime("%d%m%Y")}.pdf'
    pdf_path = os.path.join(current_app.instance_path, 'temp_pdfs', filename)
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    # Generate and save PDF
    weasyprint.HTML(string=html, base_url=request.base_url).write_pdf(pdf_path)
    
    # Return for download
    return send_from_directory(os.path.join(current_app.instance_path, 'temp_pdfs'), filename, as_attachment=True)


def _perform_quote_to_invoice_conversion(quote, quote_id):
    """Convierte una cotización en factura. Devuelve redirect o None si ya redirigió por estado previo."""
    if quote.status == 'facturada':
        flash('Esta cotización ya ha sido convertida a factura.', 'info')
        existing_invoice = Invoice.query.filter_by(quote_id=quote.id).first()
        if existing_invoice:
            from app.routes.invoice import generate_view_token as gen_inv_token
            inv_token = gen_inv_token(existing_invoice.id, 'invoice')
            return redirect(url_for('invoices.view_invoice', id=existing_invoice.id, token=inv_token))
        return redirect_to_view_quote(quote_id)

    if not quote.items.count():
        flash('La cotización no tiene ítems. Agregue productos antes de convertir a factura.', 'warning')
        return redirect_to_view_quote(quote_id)

    company_id = get_current_company_id() or quote.company_id or resolve_entity_company_id(quote)
    if not company_id:
        flash('No se pudo determinar la empresa de la cotización. Contacte al administrador.', 'danger')
        return redirect_to_view_quote(quote_id)

    try:
        if not quote.company_id:
            quote.company_id = company_id
        if quote.client_id:
            client = db.session.get(Client, quote.client_id)
            if client and not client.company_id:
                client.company_id = company_id
        db.session.flush()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception('Error al asignar company_id a cotización %s: %s', quote.id, exc)
        flash('No se pudo preparar la cotización para facturar. Contacte al administrador.', 'danger')
        return redirect_to_view_quote(quote_id)

    today = datetime.date.today()
    today_dt = datetime.datetime.combine(today, datetime.time.min)
    due_date = today + datetime.timedelta(days=30)

    for attempt in range(3):
        generated_invoice_number = next_invoice_number(company_id)
        try:
            new_invoice = Invoice(
                company_id=company_id,
                client_id=quote.client_id,
                invoice_number=generated_invoice_number,
                date=today_dt,
                due_date=due_date,
                subtotal=quote.subtotal or 0.0,
                discount_type=quote.discount_type or 'none',
                discount_value=quote.discount_value or 0.0,
                discount_amount=quote.discount_amount or 0.0,
                tax_rate=quote.tax_rate or 0.0,
                tax_amount=quote.tax_amount or 0.0,
                total_amount=quote.total_amount or 0.0,
                quote_id=quote.id,
            )
            db.session.add(new_invoice)
            db.session.flush()

            for quote_item in quote.items:
                db.session.add(InvoiceItem(
                    invoice_id=new_invoice.id,
                    product_id=quote_item.product_id,
                    quantity=quote_item.quantity,
                    unit_price=quote_item.unit_price,
                    total_price=quote_item.total_price,
                ))

            quote.status = 'facturada'
            db.session.commit()

            log_audit('create', 'invoice', new_invoice.id, {'from_quote_id': quote.id, 'invoice_number': new_invoice.invoice_number})

            flash(f'Cotización {quote.quote_number} convertida a Factura {new_invoice.invoice_number} con éxito.', 'success')
            from app.routes.invoice import generate_view_token as gen_inv_token
            inv_token = gen_inv_token(new_invoice.id, 'invoice')
            return redirect(url_for('invoices.view_invoice', id=new_invoice.id, token=inv_token))
        except IntegrityError:
            db.session.rollback()
            if attempt < 2:
                continue
            flash('No se pudo crear la factura: el número de factura ya existe. Intente de nuevo.', 'danger')
            return redirect_to_view_quote(quote_id)
        except Exception as exc:
            db.session.rollback()
            current_app.logger.exception('Error al convertir cotización %s a factura: %s', quote.id, exc)
            flash('No se pudo crear la factura. Verifique los datos e intente de nuevo.', 'danger')
            return redirect_to_view_quote(quote_id)


@quotes_bp.route('/<int:id>/convert_to_invoice', methods=['GET', 'POST'])
@quotes_bp.route('/<int:id>/<token>/convert_to_invoice', methods=['GET', 'POST'])
@login_required
def convert_to_invoice(id, token=None):
    try:
        if token and not validate_view_token(token, id, 'quote'):
            from flask import abort
            abort(404)
        elif token is None:
            from flask import abort
            abort(404)

        quote = ensure_company_id(id, Quote)
        return _perform_quote_to_invoice_conversion(quote, id)
    except Exception as exc:
        db.session.rollback()
        from werkzeug.exceptions import HTTPException
        if isinstance(exc, HTTPException):
            raise
        current_app.logger.exception('Error inesperado en convert_to_invoice(%s): %s', id, exc)
        flash('No se pudo crear la factura. Intente de nuevo o contacte al administrador.', 'danger')
        return redirect_to_view_quote(id)

@quotes_bp.route('/<int:id>/send_email', methods=['GET', 'POST'])
@quotes_bp.route('/<int:id>/<token>/send_email', methods=['GET', 'POST'])
@login_required
def send_quote_email(id, token=None):
    # Si hay token, validarlo
    if token and not validate_view_token(token, id, 'quote'):
        from flask import abort
        abort(404)
    # Si no hay token, devolver 404 (URLs antiguas no son válidas)
    elif token is None:
        from flask import abort
        abort(404)
    
    quote = ensure_company_id(id, Quote)
    # For simplicity, let's assume the recipient email is the client's email
    recipient_email = quote.client.email

    if request.method == 'POST':
        # Recalcular totales y generar PDF sin IVA (igual que Generar PDF)
        calculate_quote_totals(quote)
        net_total = float(quote.subtotal) - float(quote.discount_amount or 0)
        amount_in_words = num2words(net_total, lang='es').upper() + ' PESOS M/CTE.'
        logo_disk_path = Path(os.path.join(current_app.root_path, 'img', '1.png'))
        logo_path = urllib.parse.urljoin('file:', urllib.request.pathname2url(str(logo_disk_path))) if logo_disk_path.exists() else None
        html = render_template('quotes/pdf_template.html', quote=quote, logo_path=logo_path, amount_in_words=amount_in_words, total_neto=net_total)
        pdf_content = weasyprint.HTML(string=html, base_url=request.base_url).write_pdf()

        msg = Message(
            subject=f'Cotización #{quote.quote_number}',
            recipients=[recipient_email],
            body=f"""Estimado/a {quote.client.name},

Adjunto encontrará la cotización #{quote.quote_number}.

Saludos,
Su Empresa""",
            html=render_template('emails/quote_email.html', quote=quote) # Optional: HTML body
        )
        msg.attach(
            f'cotizacion_{quote.quote_number}.pdf',
            'application/pdf',
            pdf_content
        )
        try:
            mail.send(msg)
            flash('Correo enviado con éxito.', 'success')
        except Exception as e:
            flash(f'Error al enviar el correo: {e}', 'danger')
        return redirect_to_view_quote(id)

    # For GET request, just render a confirmation page or a simple form to confirm recipient
    return render_template('quotes/send_email_confirm.html', quote=quote, recipient_email=recipient_email, title=f'Enviar Cotización #{quote.quote_number} por Email', view_token=token)

@quotes_bp.route('/<int:id>/send_whatsapp', methods=['POST'])
@quotes_bp.route('/<int:id>/<token>/send_whatsapp', methods=['POST'])
@login_required
def send_quote_whatsapp(id, token=None):
    # Si hay token, validarlo
    if token and not validate_view_token(token, id, 'quote'):
        from flask import abort
        abort(404)
    # Si no hay token, devolver 404 (URLs antiguas no son válidas)
    elif token is None:
        from flask import abort
        abort(404)
    
    quote = ensure_company_id(id, Quote)
    client_phone = quote.client.whatsapp_number

    if not client_phone:
        flash('El cliente no tiene un número de WhatsApp registrado.', 'danger')
        return redirect_to_view_quote(id)

    try:
        # Formatear el mensaje
        message_body = f"""
*¡Hola, {quote.client.name}!*

Te enviamos los detalles de tu cotización *#{quote.quote_number}*.

*Fecha:* {quote.date.strftime('%d/%m/%Y')}
*Total:* ${quote.total_amount:,.2f}

*Ítems:*
"""
        for item in quote.items:
            message_body += f"- {item.quantity}x {item.product.name} - ${item.total_price:,.2f}\n"

        message_body += """
Gracias por tu interés.
*Laverdez S.A.S*
"""
        
        # Enviar mensaje
        success, response = send_whatsapp_message(to=client_phone, message=message_body)

        if success:
            flash('Mensaje de WhatsApp enviado con éxito.', 'success')
        else:
            flash(f"Error al enviar el mensaje de WhatsApp: {response.get('error', {}).get('message', 'Error desconocido')}", 'danger')

    except Exception as e:
        flash(f'Ocurrió un error inesperado: {e}', 'danger')

    return redirect_to_view_quote(id)

