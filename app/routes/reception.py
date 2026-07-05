# Recepción de mercancía en Bodega Principal Mayorista (clasificación a Farmacia o Almacén General)
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import (
    Reception, ReceptionItem, Warehouse, ProductWarehouseStock,
    Product, InventoryMovement
)
from app.forms import ReceptionForm
from app.tenant import filter_by_company, ensure_company_id, get_current_company_id
from app.decorators import role_required, log_audit
from datetime import datetime

reception_bp = Blueprint('reception', __name__, url_prefix='/reception')


def _next_reception_number(company_id):
    last = Reception.query.filter_by(company_id=company_id).order_by(Reception.id.desc()).first()
    n = (int(last.reception_number.replace('REC-', '')) + 1) if (last and last.reception_number and last.reception_number.startswith('REC-')) else 1
    return f'REC-{n:05d}'


def _classification_warehouses(company_id):
    """Bodegas del centro de acopio (todas las activas) para clasificar ítems recibidos. Misma fuente que Administración de almacenes."""
    return Warehouse.query.filter(
        Warehouse.company_id == company_id,
        Warehouse.active == True
    ).order_by(Warehouse.name).all()


@reception_bp.route('/')
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal'])
def list_receptions():
    from sqlalchemy import or_
    base = filter_by_company(Reception.query, Reception)
    q = request.args.get('q', '').strip()
    if q:
        base = base.filter(or_(
            Reception.reception_number.ilike(f'%{q}%'),
            Reception.guide_number.ilike(f'%{q}%')
        ))
    status = request.args.get('status', '').strip()
    if status:
        base = base.filter(Reception.status == status)
    date_from = request.args.get('date_from', '').strip()
    if date_from:
        try:
            from datetime import datetime as dt
            d = dt.strptime(date_from, '%Y-%m-%d').date()
            base = base.filter(Reception.date >= dt.combine(d, dt.min.time()))
        except ValueError:
            pass
    date_to = request.args.get('date_to', '').strip()
    if date_to:
        try:
            from datetime import datetime as dt
            d = dt.strptime(date_to, '%Y-%m-%d').date()
            base = base.filter(Reception.date <= dt.combine(d, dt.max.time()))
        except ValueError:
            pass
    receptions = base.order_by(Reception.date.desc(), Reception.id.desc()).all()
    return render_template(
        'reception/list.html',
        receptions=receptions,
        title='Recepciones',
        filter_action_route='reception.list_receptions',
        filter_q=q,
        filter_status=status,
        filter_date_from=date_from,
        filter_date_to=date_to,
        filter_show_status=True,
        filter_status_options=[('', 'Todos'), ('borrador', 'Borrador'), ('confirmado', 'Confirmado'), ('anulado', 'Anulado')],
    )


@reception_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal'])
def create_reception():
    company_id = get_current_company_id()
    if not company_id:
        flash('No tiene empresa asignada.', 'danger')
        return redirect(url_for('reception.list_receptions'))
    warehouses = _classification_warehouses(company_id)
    if not warehouses:
        flash('Configure al menos una sección del centro de acopio (Almacén General, Farmacia) en Administración.', 'warning')
        return redirect(url_for('reception.list_receptions'))
    form = ReceptionForm()
    if form.validate_on_submit():
        today = form.date.data
        rec = Reception(
            company_id=company_id,
            reception_number=_next_reception_number(company_id),
            date=datetime.combine(today, datetime.min.time()),
            guide_number=form.guide_number.data or None,
            status='borrador',
            notes=form.notes.data or None,
        )
        db.session.add(rec)
        db.session.commit()
        flash(f'Recepción {rec.reception_number} creada. Agregue ítems y clasifique destino (Farmacia / Almacén General).', 'success')
        return redirect(url_for('reception.edit_reception', id=rec.id))
    if request.method == 'GET':
        form.date.data = datetime.utcnow().date()
    return render_template('reception/form.html', form=form, reception=None, warehouses=warehouses, title='Nueva Recepción')


def _get_reception(id):
    return ensure_company_id(id, Reception)


@reception_bp.route('/<int:id>')
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal'])
def view_reception(id):
    rec = _get_reception(id)
    return render_template('reception/detail.html', reception=rec, title=f'Recepción {rec.reception_number}')


@reception_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal'])
def edit_reception(id):
    rec = _get_reception(id)
    if rec.status != 'borrador':
        flash('Solo se pueden editar recepciones en borrador.', 'warning')
        return redirect(url_for('reception.view_reception', id=id))
    company_id = rec.company_id
    warehouses = _classification_warehouses(company_id)
    form = ReceptionForm()
    if form.validate_on_submit():
        rec.date = datetime.combine(form.date.data, datetime.min.time())
        rec.guide_number = form.guide_number.data or None
        rec.notes = form.notes.data or None
        db.session.commit()
        flash('Cabecera actualizada.', 'success')
        return redirect(url_for('reception.edit_reception', id=id))
    if request.method == 'GET':
        form.date.data = rec.date.date() if rec.date else datetime.utcnow().date()
        form.guide_number.data = rec.guide_number
        form.notes.data = rec.notes
    products = Product.query.filter_by(company_id=company_id).order_by(Product.name).all()
    return render_template(
        'reception/form.html',
        form=form,
        reception=rec,
        warehouses=warehouses,
        products=products,
        title=f'Editar {rec.reception_number}',
    )


@reception_bp.route('/<int:id>/add-item', methods=['POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal'])
def add_reception_item(id):
    rec = _get_reception(id)
    if rec.status != 'borrador':
        flash('Solo se pueden agregar ítems a recepciones en borrador.', 'warning')
        return redirect(url_for('reception.edit_reception', id=id))
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', type=int)
    warehouse_id = request.form.get('warehouse_id', type=int)
    if not product_id or not quantity or quantity < 1 or not warehouse_id:
        flash('Producto, cantidad y bodega destino son obligatorios.', 'danger')
        return redirect(url_for('reception.edit_reception', id=id))
    product = Product.query.filter_by(id=product_id, company_id=rec.company_id).first_or_404()
    wh = Warehouse.query.filter(
        Warehouse.id == warehouse_id,
        Warehouse.company_id == rec.company_id,
        Warehouse.active == True,
        Warehouse.warehouse_type.in_(('general', 'farmacia', 'mayorista'))
    ).first()
    if not wh:
        flash('Sección no válida (elija Almacén General o Farmacia).', 'danger')
        return redirect(url_for('reception.edit_reception', id=id))
    existing = next((i for i in rec.items if i.product_id == product_id and i.warehouse_id == warehouse_id), None)
    if existing:
        existing.quantity += quantity
    else:
        rec.items.append(ReceptionItem(product_id=product_id, quantity=quantity, warehouse_id=warehouse_id))
    db.session.commit()
    flash(f'Ítem agregado: {product.name} x {quantity} → {wh.name}', 'success')
    return redirect(url_for('reception.edit_reception', id=id))


@reception_bp.route('/<int:id>/update-item/<int:item_id>', methods=['POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal'])
def update_reception_item(id, item_id):
    """Actualiza cantidad y/o destino de un ítem de la recepción (solo borrador)."""
    rec = _get_reception(id)
    if rec.status != 'borrador':
        flash('Solo se pueden editar ítems en recepciones en borrador.', 'warning')
        return redirect(url_for('reception.edit_reception', id=id))
    item = ReceptionItem.query.filter_by(id=item_id, reception_id=id).first_or_404()
    quantity = request.form.get('quantity', type=int)
    warehouse_id = request.form.get('warehouse_id', type=int)
    if not quantity or quantity < 1:
        flash('Cantidad inválida.', 'danger')
        return redirect(url_for('reception.edit_reception', id=id))
    if not warehouse_id:
        flash('Debe elegir bodega de destino.', 'danger')
        return redirect(url_for('reception.edit_reception', id=id))
    wh = Warehouse.query.filter_by(id=warehouse_id, company_id=rec.company_id, active=True).first()
    if not wh:
        flash('Bodega no válida.', 'danger')
        return redirect(url_for('reception.edit_reception', id=id))
    item.quantity = quantity
    item.warehouse_id = warehouse_id
    db.session.commit()
    flash('Ítem actualizado.', 'success')
    return redirect(url_for('reception.edit_reception', id=id))


@reception_bp.route('/<int:id>/remove-item/<int:item_id>', methods=['POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal'])
def remove_reception_item(id, item_id):
    rec = _get_reception(id)
    if rec.status != 'borrador':
        flash('Solo se pueden quitar ítems de recepciones en borrador.', 'warning')
        return redirect(url_for('reception.edit_reception', id=id))
    item = ReceptionItem.query.filter_by(id=item_id, reception_id=id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash('Ítem quitado.', 'success')
    return redirect(url_for('reception.edit_reception', id=id))


@reception_bp.route('/<int:id>/confirm', methods=['POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal'])
def confirm_reception(id):
    rec = _get_reception(id)
    if rec.status != 'borrador':
        flash('Esta recepción ya está confirmada o anulada.', 'warning')
        return redirect(url_for('reception.view_reception', id=id))
    if not rec.items:
        flash('Agregue al menos un ítem antes de confirmar.', 'danger')
        return redirect(url_for('reception.edit_reception', id=id))
    product_ids_affected = set()
    for item in rec.items:
        pws = ProductWarehouseStock.query.filter_by(
            product_id=item.product_id, warehouse_id=item.warehouse_id
        ).first()
        if pws:
            pws.quantity += item.quantity
        else:
            pws = ProductWarehouseStock(
                product_id=item.product_id,
                warehouse_id=item.warehouse_id,
                quantity=item.quantity,
            )
            db.session.add(pws)
        product_ids_affected.add(item.product_id)
    for pid in product_ids_affected:
        product = Product.query.get(pid)
        if product:
            new_total = sum(p.quantity for p in ProductWarehouseStock.query.filter_by(product_id=pid).all())
            prev_total = product.stock
            product.stock = new_total
            movement = InventoryMovement(
                product_id=product.id,
                movement_type='reception',
                quantity=new_total - prev_total,
                previous_stock=prev_total,
                new_stock=new_total,
                reference_type='reception',
                reference_id=rec.id,
                user_id=current_user.id,
                notes=f'Recepción {rec.reception_number}',
                created_at=datetime.utcnow(),
            )
            db.session.add(movement)
    rec.status = 'confirmado'
    rec.received_by_user_id = current_user.id
    rec.received_at = datetime.utcnow()
    db.session.commit()
    log_audit('update', 'reception', rec.id, {'action': 'confirm', 'reception_number': rec.reception_number})
    flash(f'Recepción {rec.reception_number} confirmada. Stock actualizado en Farmacia/Almacén General.', 'success')
    return redirect(url_for('reception.view_reception', id=id))


@reception_bp.route('/<int:id>/cancel', methods=['POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal'])
def cancel_reception(id):
    rec = _get_reception(id)
    if rec.status != 'borrador':
        flash('Solo se puede anular una recepción en borrador.', 'warning')
        return redirect(url_for('reception.view_reception', id=id))
    rec.status = 'anulado'
    db.session.commit()
    flash('Recepción anulada.', 'success')
    return redirect(url_for('reception.list_receptions'))
