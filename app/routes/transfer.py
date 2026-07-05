# Traslados entre secciones del centro de acopio (Almacén General <-> Farmacia)
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Warehouse, WarehouseTransfer, WarehouseTransferItem, ProductWarehouseStock, Product, InventoryMovement
from app.forms import WarehouseTransferForm, WarehouseTransferItemForm
from app.tenant import filter_by_company, ensure_company_id, get_current_company_id
from app.decorators import role_required, log_audit
from datetime import datetime

transfer_bp = Blueprint('transfer', __name__, url_prefix='/transfers')

SECTION_LABELS = {'general': 'Almacén General', 'farmacia': 'Farmacia', 'mayorista': 'Almacén General', 'minorista': 'Farmacia'}


def _section_warehouses(company_id):
    """Bodegas del centro de acopio de la empresa (todas las activas) para traslados entre ellas."""
    return Warehouse.query.filter(
        Warehouse.company_id == company_id,
        Warehouse.active == True
    ).order_by(Warehouse.name).all()


def _next_transfer_number(company_id):
    last = WarehouseTransfer.query.filter_by(company_id=company_id).order_by(WarehouseTransfer.id.desc()).first()
    n = (int(last.transfer_number.replace('TRAS-', '')) + 1) if (last and last.transfer_number and last.transfer_number.startswith('TRAS-')) else 1
    return f'TRAS-{n:05d}'


@transfer_bp.route('/')
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal'])
def list_transfers():
    base = filter_by_company(WarehouseTransfer.query, WarehouseTransfer)
    q = request.args.get('q', '').strip()
    if q:
        base = base.filter(WarehouseTransfer.transfer_number.ilike(f'%{q}%'))
    status = request.args.get('status', '').strip()
    if status:
        base = base.filter(WarehouseTransfer.status == status)
    date_from = request.args.get('date_from', '').strip()
    if date_from:
        try:
            d = datetime.strptime(date_from, '%Y-%m-%d').date()
            base = base.filter(WarehouseTransfer.date >= datetime.combine(d, datetime.min.time()))
        except ValueError:
            pass
    date_to = request.args.get('date_to', '').strip()
    if date_to:
        try:
            d = datetime.strptime(date_to, '%Y-%m-%d').date()
            base = base.filter(WarehouseTransfer.date <= datetime.combine(d, datetime.max.time()))
        except ValueError:
            pass
    transfers = base.order_by(WarehouseTransfer.date.desc(), WarehouseTransfer.id.desc()).all()
    return render_template(
        'transfer/list.html',
        transfers=transfers,
        title='Traslados entre Bodegas',
        filter_action_route='transfer.list_transfers',
        filter_q=q,
        filter_status=status,
        filter_date_from=date_from,
        filter_date_to=date_to,
        filter_show_status=True,
        filter_status_options=[('', 'Todos'), ('borrador', 'Borrador'), ('confirmado', 'Confirmado'), ('anulado', 'Anulado')],
    )


@transfer_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal'])
def create_transfer():
    company_id = get_current_company_id()
    if not company_id:
        flash('No tiene empresa asignada.', 'danger')
        return redirect(url_for('transfer.list_transfers'))
    warehouses = _section_warehouses(company_id)
    if len(warehouses) < 2:
        flash('Configure las dos secciones del centro de acopio (Almacén General y Farmacia) en Administración.', 'warning')
        return redirect(url_for('transfer.list_transfers'))
    form = WarehouseTransferForm()
    form.warehouse_origin_id.choices = [(w.id, f"{w.name} ({SECTION_LABELS.get(w.warehouse_type, w.warehouse_type)})") for w in warehouses]
    form.warehouse_dest_id.choices = [(w.id, f"{w.name} ({SECTION_LABELS.get(w.warehouse_type, w.warehouse_type)})") for w in warehouses]
    # Fecha automática (hoy) en nuevo traslado
    today = datetime.utcnow().date()
    form.date.data = today
    if form.validate_on_submit():
        if form.warehouse_origin_id.data == form.warehouse_dest_id.data:
            flash('Origen y destino deben ser diferentes.', 'danger')
            return render_template('transfer/form.html', form=form, transfer=None, warehouses=warehouses, title='Nuevo Traslado')
        transfer = WarehouseTransfer(
            company_id=company_id,
            warehouse_origin_id=form.warehouse_origin_id.data,
            warehouse_dest_id=form.warehouse_dest_id.data,
            transfer_number=_next_transfer_number(company_id),
            date=datetime.combine(today, datetime.min.time()),
            status='borrador',
            notes=form.notes.data
        )
        db.session.add(transfer)
        db.session.commit()
        flash(f'Traslado {transfer.transfer_number} creado. Agregue ítems.', 'success')
        return redirect(url_for('transfer.edit_transfer', id=transfer.id))
    return render_template('transfer/form.html', form=form, transfer=None, warehouses=warehouses, title='Nuevo Traslado')


@transfer_bp.route('/<int:id>')
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal'])
def view_transfer(id):
    transfer = _get_transfer(id)
    return render_template('transfer/detail.html', transfer=transfer, title=f'Traslado {transfer.transfer_number}')


def _get_transfer(id):
    return ensure_company_id(id, WarehouseTransfer)


@transfer_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal'])
def edit_transfer(id):
    transfer = _get_transfer(id)
    if transfer.status != 'borrador':
        flash('Solo se pueden editar traslados en borrador.', 'warning')
        return redirect(url_for('transfer.view_transfer', id=transfer.id))
    company_id = transfer.company_id
    warehouses = _section_warehouses(company_id)
    form = WarehouseTransferForm()
    form.warehouse_origin_id.choices = [(w.id, f"{w.name} ({SECTION_LABELS.get(w.warehouse_type, w.warehouse_type)})") for w in warehouses]
    form.warehouse_dest_id.choices = [(w.id, f"{w.name} ({SECTION_LABELS.get(w.warehouse_type, w.warehouse_type)})") for w in warehouses]
    if form.validate_on_submit():
        transfer.warehouse_origin_id = form.warehouse_origin_id.data
        transfer.warehouse_dest_id = form.warehouse_dest_id.data
        # La fecha no se edita: se mantiene la original del traslado
        transfer.notes = form.notes.data
        db.session.commit()
        flash('Traslado actualizado.', 'success')
        return redirect(url_for('transfer.edit_transfer', id=transfer.id))
    if request.method == 'GET':
        form.warehouse_origin_id.data = transfer.warehouse_origin_id
        form.warehouse_dest_id.data = transfer.warehouse_dest_id
        form.date.data = transfer.date.date() if transfer.date else datetime.utcnow().date()
        form.notes.data = transfer.notes
    products = Product.query.filter_by(company_id=company_id).order_by(Product.name).all()
    item_form = WarehouseTransferItemForm()
    item_form.product_id.choices = [(p.id, f"{p.code} - {p.name}") for p in products]
    return render_template('transfer/edit.html', transfer=transfer, form=form, item_form=item_form, products=products, title=f'Editar {transfer.transfer_number}')


@transfer_bp.route('/<int:id>/add-item', methods=['POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal'])
def add_transfer_item(id):
    transfer = _get_transfer(id)
    if transfer.status != 'borrador':
        flash('Solo se pueden agregar ítems a traslados en borrador.', 'warning')
        return redirect(url_for('transfer.edit_transfer', id=id))
    product_id = request.form.get('product_id', type=int)
    quantity_boxes = request.form.get('quantity_boxes', type=int)
    quantity = request.form.get('quantity', type=int)
    if product_id:
        product_for_boxes = Product.query.get(product_id)
        if quantity_boxes is not None and quantity_boxes > 0 and product_for_boxes and product_for_boxes.units_per_package:
            quantity = quantity_boxes * product_for_boxes.units_per_package
    if not product_id or not quantity or quantity < 1:
        flash('Cantidad inválida.', 'danger')
        return redirect(url_for('transfer.edit_transfer', id=id))
    product = Product.query.filter_by(id=product_id, company_id=transfer.company_id).first_or_404()
    pws = ProductWarehouseStock.query.filter_by(product_id=product_id, warehouse_id=transfer.warehouse_origin_id).first()
    available = (pws.quantity if pws else 0)
    existing = sum(i.quantity for i in transfer.items if i.product_id == product_id)
    available -= existing
    if quantity > available:
        flash(f'Stock insuficiente en bodega origen para {product.name}. Disponible: {available}', 'danger')
        return redirect(url_for('transfer.edit_transfer', id=id))
    existing_item = next((i for i in transfer.items if i.product_id == product_id), None)
    if existing_item:
        existing_item.quantity += quantity
    else:
        transfer.items.append(WarehouseTransferItem(product_id=product_id, quantity=quantity))
    db.session.commit()
    flash(f'Ítem agregado: {product.name} x {quantity}', 'success')
    return redirect(url_for('transfer.edit_transfer', id=id))


@transfer_bp.route('/<int:id>/update-item/<int:item_id>', methods=['POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal'])
def update_transfer_item(id, item_id):
    """Actualiza la cantidad de un ítem del traslado (solo borrador)."""
    transfer = _get_transfer(id)
    if transfer.status != 'borrador':
        flash('Solo se pueden editar ítems en traslados en borrador.', 'warning')
        return redirect(url_for('transfer.edit_transfer', id=id))
    item = WarehouseTransferItem.query.filter_by(id=item_id, transfer_id=id).first_or_404()
    quantity_boxes = request.form.get('quantity_boxes', type=int)
    quantity = request.form.get('quantity', type=int)
    if quantity_boxes is not None and quantity_boxes > 0 and item.product.units_per_package:
        quantity = quantity_boxes * item.product.units_per_package
    if not quantity or quantity < 1:
        flash('Cantidad inválida.', 'danger')
        return redirect(url_for('transfer.edit_transfer', id=id))
    pws = ProductWarehouseStock.query.filter_by(
        product_id=item.product_id, warehouse_id=transfer.warehouse_origin_id
    ).first()
    available = (pws.quantity if pws else 0)
    other_items_qty = sum(i.quantity for i in transfer.items if i.id != item_id and i.product_id == item.product_id)
    available -= other_items_qty
    if quantity > available:
        flash(f'Stock insuficiente en bodega origen. Disponible: {available}', 'danger')
        return redirect(url_for('transfer.edit_transfer', id=id))
    item.quantity = quantity
    db.session.commit()
    flash('Cantidad actualizada.', 'success')
    return redirect(url_for('transfer.edit_transfer', id=id))


@transfer_bp.route('/<int:id>/remove-item/<int:item_id>', methods=['POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal'])
def remove_transfer_item(id, item_id):
    transfer = _get_transfer(id)
    if transfer.status != 'borrador':
        flash('Solo se pueden quitar ítems de traslados en borrador.', 'warning')
        return redirect(url_for('transfer.edit_transfer', id=id))
    item = WarehouseTransferItem.query.filter_by(id=item_id, transfer_id=id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash('Ítem quitado.', 'success')
    return redirect(url_for('transfer.edit_transfer', id=id))


@transfer_bp.route('/<int:id>/confirm', methods=['POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal'])
def confirm_transfer(id):
    transfer = _get_transfer(id)
    if transfer.status != 'borrador':
        flash('Este traslado ya está confirmado o anulado.', 'warning')
        return redirect(url_for('transfer.view_transfer', id=id))
    if not transfer.items:
        flash('Agregue al menos un ítem antes de confirmar.', 'danger')
        return redirect(url_for('transfer.edit_transfer', id=id))
    product_ids_affected = set()
    for item in transfer.items:
        pws_origin = ProductWarehouseStock.query.filter_by(
            product_id=item.product_id, warehouse_id=transfer.warehouse_origin_id
        ).first()
        pws_dest = ProductWarehouseStock.query.filter_by(
            product_id=item.product_id, warehouse_id=transfer.warehouse_dest_id
        ).first()
        if not pws_origin or pws_origin.quantity < item.quantity:
            flash(f'Stock insuficiente para {item.product.name} en bodega origen.', 'danger')
            return redirect(url_for('transfer.edit_transfer', id=id))
        pws_origin.quantity -= item.quantity
        if pws_dest:
            pws_dest.quantity += item.quantity
        else:
            pws_dest = ProductWarehouseStock(product_id=item.product_id, warehouse_id=transfer.warehouse_dest_id, quantity=item.quantity)
            db.session.add(pws_dest)
        product_ids_affected.add(item.product_id)
    for pid in product_ids_affected:
        product = Product.query.get(pid)
        if product:
            new_total = sum(p.quantity for p in ProductWarehouseStock.query.filter_by(product_id=pid).all())
            prev_total = product.stock
            product.stock = new_total
            movement = InventoryMovement(
                product_id=product.id,
                movement_type='transfer',
                quantity=0,
                previous_stock=prev_total,
                new_stock=new_total,
                reference_type='transfer',
                reference_id=transfer.id,
                user_id=current_user.id,
                notes=f'Traslado {transfer.transfer_number}'
            )
            db.session.add(movement)
    transfer.status = 'confirmado'
    db.session.commit()
    log_audit('update', 'transfer', transfer.id, {'action': 'confirm', 'transfer_number': transfer.transfer_number})
    flash(f'Traslado {transfer.transfer_number} confirmado. Stock actualizado.', 'success')
    return redirect(url_for('transfer.view_transfer', id=id))


@transfer_bp.route('/<int:id>/cancel', methods=['POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal'])
def cancel_transfer(id):
    transfer = _get_transfer(id)
    if transfer.status != 'borrador':
        flash('Solo se puede anular un traslado en borrador.', 'warning')
        return redirect(url_for('transfer.view_transfer', id=id))
    transfer.status = 'anulado'
    db.session.commit()
    flash('Traslado anulado.', 'success')
    return redirect(url_for('transfer.list_transfers'))
