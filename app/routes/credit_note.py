from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, current_app
import os
from flask_login import login_required, current_user
from app import db, mail
from flask_mail import Message
from app.models import CreditNote, CreditNoteItem, Invoice, InvoiceItem, Product, InventoryMovement, Client
from app.forms import CreditNoteForm, CreditNoteItemForm
from app.tenant import filter_by_company, ensure_company_id, get_company_default_tax_rate
import datetime
import weasyprint
from pathlib import Path
import urllib.parse
import urllib.request
from num2words import num2words
from config import Config
from itsdangerous import URLSafeTimedSerializer

credit_notes_bp = Blueprint('credit_notes', __name__, url_prefix='/credit_notes')

def generate_view_token(entity_id, entity_type='credit_note', expires_in=3600):
    """Genera un token temporal para acceder a una vista"""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    data = f"{entity_type}:{entity_id}"
    return serializer.dumps(data, salt='view-token')

def validate_view_token(token, entity_id, entity_type='credit_note', max_age=3600):
    """Valida un token temporal"""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        data = serializer.loads(token, salt='view-token', max_age=max_age)
        expected = f"{entity_type}:{entity_id}"
        return data == expected
    except:
        return False

def validate_id_format(id_value, blueprint_prefix='credit_notes'):
    """
    Valida que el ID en la URL no tenga ceros a la izquierda.
    Previene acceso no autorizado con URLs como '/credit_notes/09' -> 9
    """
    path_parts = request.path.strip('/').split('/')
    if len(path_parts) >= 2 and path_parts[0] == blueprint_prefix:
        url_id_str = path_parts[1]
        # Si el string original tiene ceros a la izquierda o no coincide con el ID convertido, es inválido
        if url_id_str != str(id_value) or (url_id_str.startswith('0') and len(url_id_str) > 1):
            from flask import abort
            abort(404)

def calculate_credit_note_totals(credit_note):
    """
    Calcula subtotal, discount_amount, tax_amount y total_amount de una nota de crédito.
    """
    subtotal = sum(item.total_price for item in credit_note.items)
    
    # Calcular descuento
    discount_amount = 0.0
    if credit_note.discount_type == 'percentage':
        discount_amount = subtotal * (credit_note.discount_value / 100.0)
    elif credit_note.discount_type == 'amount':
        discount_amount = min(credit_note.discount_value, subtotal)
    
    amount_after_discount = subtotal - discount_amount

    # Sin IVA: total = valor neto (subtotal - descuento)
    tax_rate = 0.0
    tax_amount = 0.0
    total_amount = amount_after_discount
    
    credit_note.subtotal = subtotal
    credit_note.discount_amount = discount_amount
    credit_note.tax_rate = tax_rate
    credit_note.tax_amount = tax_amount
    credit_note.total_amount = total_amount
    
    return subtotal, discount_amount, tax_amount, total_amount

@credit_notes_bp.route('/')
@login_required
def list_credit_notes():
    """Lista todas las notas de crédito."""
    from sqlalchemy import or_
    base_query = filter_by_company(CreditNote.query, CreditNote)
    q = request.args.get('q', '').strip()
    if q:
        base_query = base_query.join(Invoice, CreditNote.invoice_id == Invoice.id).join(Client, Invoice.client_id == Client.id).filter(
            or_(
                CreditNote.credit_note_number.ilike(f'%{q}%'),
                Invoice.invoice_number.ilike(f'%{q}%'),
                Client.name.ilike(f'%{q}%'),
                Client.document_number.ilike(f'%{q}%')
            )
        )
    date_from = request.args.get('date_from', '').strip()
    if date_from:
        try:
            from datetime import datetime as dt
            d = dt.strptime(date_from, '%Y-%m-%d').date()
            base_query = base_query.filter(CreditNote.date >= dt.combine(d, dt.min.time()))
        except ValueError:
            pass
    date_to = request.args.get('date_to', '').strip()
    if date_to:
        try:
            from datetime import datetime as dt
            d = dt.strptime(date_to, '%Y-%m-%d').date()
            base_query = base_query.filter(CreditNote.date <= dt.combine(d, dt.max.time()))
        except ValueError:
            pass
    status = request.args.get('status', '').strip()
    if status:
        base_query = base_query.filter(CreditNote.status == status)
    credit_notes = base_query.order_by(CreditNote.date.desc()).all()
    return render_template(
        'credit_notes/list.html',
        credit_notes=credit_notes,
        title='Notas de Crédito',
        filter_q=q,
        filter_date_from=date_from,
        filter_date_to=date_to,
        filter_status=status,
        filter_show_status=True,
        filter_status_options=[('', 'Todos'), ('active', 'Activa')],
    )

@credit_notes_bp.route('/new/<int:invoice_id>', methods=['GET', 'POST'])
@login_required
def create_from_invoice(invoice_id):
    """Crea una nota de crédito desde una factura específica."""
    invoice = ensure_company_id(invoice_id, Invoice)
    form = CreditNoteForm()
    
    # Pre-llenar datos de la factura
    form.invoice_id.choices = [(invoice.id, f"Factura #{invoice.invoice_number}")]
    
    # Generar número de nota de crédito (único por empresa)
    base_credit_note_query = filter_by_company(CreditNote.query, CreditNote)
    last_credit_note = base_credit_note_query.order_by(CreditNote.id.desc()).first()
    if last_credit_note and last_credit_note.credit_note_number.isdigit():
        next_number = int(last_credit_note.credit_note_number) + 1
    else:
        next_number = 1
    
    generated_number = str(next_number).zfill(4)
    
    if form.validate_on_submit():
        tax_rate = form.tax_rate.data if form.tax_rate.data is not None else get_company_default_tax_rate(invoice.company_id)
        
        new_credit_note = CreditNote(
            credit_note_number=generated_number,
            invoice_id=invoice.id,
            date=form.date.data,
            reason=form.reason.data,
            company_id=current_user.company_id,
            subtotal=0.0,
            discount_type=form.discount_type.data or 'none',
            discount_value=form.discount_value.data or 0.0,
            discount_amount=0.0,
            tax_rate=tax_rate,
            tax_amount=0.0,
            total_amount=0.0,
            status='active'
        )
        db.session.add(new_credit_note)
        db.session.commit()
        flash('Nota de crédito creada. Ahora puede añadir ítems a devolver.', 'success')
        return redirect(url_for('credit_notes.view_credit_note', id=new_credit_note.id))
    
    if not form.is_submitted():
        form.date.data = datetime.date.today()
        form.tax_rate.data = get_company_default_tax_rate(invoice.company_id)
        form.discount_type.data = invoice.discount_type or 'none'
        form.discount_value.data = invoice.discount_value or 0.0
    
    return render_template('credit_notes/form.html', form=form, invoice=invoice, title='Nueva Nota de Crédito')

@credit_notes_bp.route('/<string:invalid_id>')
@login_required
def invalid_credit_note_id(invalid_id):
    """Maneja IDs inválidos (strings) y devuelve 404 después de verificar autenticación"""
    from flask import abort
    abort(404)

@credit_notes_bp.route('/<int:id>', methods=['GET', 'POST'])
@login_required
def view_credit_note(id):
    """Vista detallada de una nota de crédito y permite añadir ítems."""
    # Validar formato del ID para prevenir acceso no autorizado
    validate_id_format(id, 'credit_notes')
    credit_note = ensure_company_id(id, CreditNote)
    item_form = CreditNoteItemForm()
    
    # Obtener ítems de la factura original que aún no han sido devueltos completamente
    invoice = credit_note.invoice
    invoice_items = []
    for inv_item in invoice.items:
        # Calcular cantidad ya devuelta en otras notas de crédito
        total_returned = sum(
            cn_item.quantity for cn in invoice.credit_notes
            for cn_item in cn.items
            if cn_item.invoice_item_id == inv_item.id
        )
        available_to_return = inv_item.quantity - total_returned
        if available_to_return > 0:
            invoice_items.append((inv_item.id, f"{inv_item.product.code} - {inv_item.product.name} (Disponible: {available_to_return})"))
    
    item_form.invoice_item_id.choices = [(None, 'Seleccione un ítem')] + invoice_items
    
    if request.method == 'POST' and 'add_item' in request.form and item_form.validate():
        # InvoiceItem no tiene company_id directamente, pero se valida a través de Invoice
        invoice_item = InvoiceItem.query.get(item_form.invoice_item_id.data)
        if invoice_item and invoice_item.invoice.company_id != current_user.company_id:
            from flask import abort
            abort(403)
        if not invoice_item or invoice_item.invoice_id != invoice.id:
            flash('Ítem de factura no válido.', 'danger')
            return redirect(url_for('credit_notes.view_credit_note', id=id))
        
        # Verificar cantidad disponible
        total_returned = sum(
            cn_item.quantity for cn in invoice.credit_notes
            for cn_item in cn.items
            if cn_item.invoice_item_id == invoice_item.id
        )
        available = invoice_item.quantity - total_returned
        
        if item_form.quantity.data > available:
            flash(f'Cantidad excede lo disponible. Disponible: {available}', 'danger')
            return redirect(url_for('credit_notes.view_credit_note', id=id))
        
        # Crear ítem de nota de crédito
        new_item = CreditNoteItem(
            credit_note_id=credit_note.id,
            invoice_item_id=invoice_item.id,
            product_id=invoice_item.product_id,
            quantity=item_form.quantity.data,
            unit_price=invoice_item.unit_price,
            total_price=item_form.quantity.data * invoice_item.unit_price
        )
        db.session.add(new_item)
        
        # Devolver productos al inventario
        product = Product.query.get(invoice_item.product_id)
        previous_stock = product.stock
        product.stock += item_form.quantity.data
        
        # Registrar movimiento de inventario
        movement = InventoryMovement(
            product_id=product.id,
            movement_type='return',
            quantity=item_form.quantity.data,
            previous_stock=previous_stock,
            new_stock=product.stock,
            reference_type='credit_note',
            reference_id=credit_note.id,
            user_id=current_user.id if current_user.is_authenticated else None,
            notes=f'Devolución por nota de crédito #{credit_note.credit_note_number}',
            created_at=datetime.datetime.utcnow()
        )
        db.session.add(movement)
        
        # Recalcular totales
        calculate_credit_note_totals(credit_note)
        
        db.session.commit()
        flash('Ítem añadido a la nota de crédito con éxito.', 'success')
        return redirect(url_for('credit_notes.view_credit_note', id=id))
    
    return render_template('credit_notes/view.html', credit_note=credit_note, item_form=item_form, title=f'Nota de Crédito #{credit_note.credit_note_number}')

@credit_notes_bp.route('/<int:id>/pdf')
@login_required
def generate_credit_note_pdf(id):
    """Genera PDF de la nota de crédito."""
    credit_note = ensure_company_id(id, CreditNote)
    logo_disk_path = Path(os.path.join(current_app.root_path, 'img', '1.png'))
    logo_path = urllib.parse.urljoin('file:', urllib.request.pathname2url(str(logo_disk_path))) if logo_disk_path.exists() else None
    
    amount_in_words = num2words(credit_note.total_amount, lang='es').upper() + ' PESOS M/CTE.'
    
    html = render_template('credit_notes/pdf_template.html', credit_note=credit_note, logo_path=logo_path, amount_in_words=amount_in_words)
    
    filename = f'nota_credito_{credit_note.credit_note_number}_{datetime.date.today().strftime("%d%m%Y")}.pdf'
    pdf_path = os.path.join(current_app.instance_path, 'temp_pdfs', filename)
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    
    weasyprint.HTML(string=html, base_url=request.base_url).write_pdf(pdf_path)
    
    return send_from_directory(os.path.join(current_app.instance_path, 'temp_pdfs'), filename, as_attachment=True)

@credit_notes_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_credit_note(id):
    """Elimina una nota de crédito (solo si no tiene ítems o está permitido)."""
    credit_note = ensure_company_id(id, CreditNote)
    
    # Revertir movimientos de inventario
    for item in credit_note.items:
        product = ensure_company_id(item.product_id, Product)
        if product:
            product.stock -= item.quantity  # Revertir la devolución
    
    db.session.delete(credit_note)
    db.session.commit()
    flash('Nota de crédito eliminada con éxito.', 'success')
    return redirect(url_for('credit_notes.list_credit_notes'))
