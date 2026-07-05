# Pedidos de despacho: punto de despacho solicita productos; bodega crea despacho y confirma entrega
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import (
    DispatchOrder, DispatchOrderItem, Delivery, DeliveryItem,
    DeliveryPoint, Warehouse, Product
)
from app.tenant import filter_by_company, ensure_company_id, get_current_company_id
from app.decorators import role_required
from datetime import datetime

dispatch_order_bp = Blueprint('dispatch_order', __name__, url_prefix='/dispatch-order')

SECTION_TYPES = ('general', 'farmacia', 'mayorista')


def _next_order_number(company_id):
    last = DispatchOrder.query.filter_by(company_id=company_id).order_by(DispatchOrder.id.desc()).first()
    n = 1
    if last and last.order_number and last.order_number.startswith('PED-'):
        try:
            n = int(last.order_number.replace('PED-', '')) + 1
        except ValueError:
            pass
    return f'PED-{n:05d}'


def _section_warehouses(company_id):
    return Warehouse.query.filter(
        Warehouse.company_id == company_id,
        Warehouse.active == True,
        Warehouse.warehouse_type.in_(SECTION_TYPES)
    ).order_by(Warehouse.name).all()


def _next_delivery_number(company_id):
    last = Delivery.query.filter_by(company_id=company_id).order_by(Delivery.id.desc()).first()
    n = (int(last.delivery_number.replace('PRE-', '')) + 1) if (last and last.delivery_number and last.delivery_number.startswith('PRE-')) else 1
    return f'PRE-{n:05d}'


@dispatch_order_bp.route('/')
@login_required
@role_required(['despachador'])
def list_my_orders():
    """Lista de pedidos del punto de despacho del usuario."""
    point = getattr(current_user, 'assigned_delivery_point', None)
    if not point:
        flash('No tiene punto de despacho asignado.', 'warning')
        return redirect(url_for('main.index'))
    company_id = get_current_company_id()
    if not company_id:
        flash('No tiene empresa asignada.', 'danger')
        return redirect(url_for('main.index'))
    base = DispatchOrder.query.filter_by(company_id=company_id, delivery_point_id=point.id)
    q = request.args.get('q', '').strip()
    if q:
        base = base.filter(DispatchOrder.order_number.ilike(f'%{q}%'))
    status = request.args.get('status', '').strip()
    if status:
        base = base.filter(DispatchOrder.status == status)
    date_from = request.args.get('date_from', '').strip()
    if date_from:
        try:
            d = datetime.strptime(date_from, '%Y-%m-%d').date()
            base = base.filter(DispatchOrder.created_at >= datetime.combine(d, datetime.min.time()))
        except ValueError:
            pass
    date_to = request.args.get('date_to', '').strip()
    if date_to:
        try:
            d = datetime.strptime(date_to, '%Y-%m-%d').date()
            base = base.filter(DispatchOrder.created_at <= datetime.combine(d, datetime.max.time()))
        except ValueError:
            pass
    orders = base.order_by(DispatchOrder.created_at.desc()).all()
    return render_template(
        'dispatch_order/list_my.html',
        orders=orders,
        title='Mis pedidos',
        filter_q=q,
        filter_status=status,
        filter_date_from=date_from or '',
        filter_date_to=date_to or '',
        filter_show_status=True,
        filter_status_options=[('', 'Todos'), ('pendiente', 'Pendiente'), ('en_preparacion', 'En preparación'), ('recibido', 'Recibido')],
    )


@dispatch_order_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required(['despachador'])
def create_order():
    """Crear nuevo pedido (despachador)."""
    point = getattr(current_user, 'assigned_delivery_point', None)
    if not point:
        flash('No tiene punto de despacho asignado.', 'warning')
        return redirect(url_for('dispatch_order.list_my_orders'))
    company_id = get_current_company_id()
    if not company_id:
        flash('No tiene empresa asignada.', 'danger')
        return redirect(url_for('dispatch_order.list_my_orders'))
    products = Product.query.filter_by(company_id=company_id).order_by(Product.name).all()
    if request.method == 'POST':
        notes = (request.form.get('notes') or '').strip() or None
        product_ids = request.form.getlist('product_id')
        quantities = request.form.getlist('quantity')
        order = DispatchOrder(
            company_id=company_id,
            delivery_point_id=point.id,
            requested_by_user_id=current_user.id,
            order_number=_next_order_number(company_id),
            status='pendiente',
            notes=notes
        )
        db.session.add(order)
        db.session.flush()
        has_items = False
        for i, product_id in enumerate(product_ids):
            try:
                pid = int(product_id)
                qty = int(quantities[i]) if i < len(quantities) else 0
                if qty > 0 and Product.query.filter_by(id=pid, company_id=company_id).first():
                    db.session.add(DispatchOrderItem(order_id=order.id, product_id=pid, quantity=qty))
                    has_items = True
            except (ValueError, TypeError):
                continue
        if not has_items:
            db.session.rollback()
            flash('Agregue al menos un producto al pedido.', 'danger')
            return redirect(url_for('dispatch_order.create_order'))
        db.session.commit()
        flash(f'Pedido {order.order_number} creado.', 'success')
        return redirect(url_for('dispatch_order.list_my_orders'))
    return render_template('dispatch_order/form.html', products=products, title='Solicitar productos')


@dispatch_order_bp.route('/pending')
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal'])
def list_pending():
    """Pedidos pendientes o en preparación (bodega/admin)."""
    from app.models import DeliveryPoint
    company_id = get_current_company_id()
    base = filter_by_company(DispatchOrder.query, DispatchOrder)
    base = base.filter(DispatchOrder.status.in_(['pendiente', 'en_preparacion']))
    q = request.args.get('q', '').strip()
    if q:
        base = base.filter(DispatchOrder.order_number.ilike(f'%{q}%'))
    status = request.args.get('status', '').strip()
    if status:
        base = base.filter(DispatchOrder.status == status)
    date_from = request.args.get('date_from', '').strip()
    if date_from:
        try:
            d = datetime.strptime(date_from, '%Y-%m-%d').date()
            base = base.filter(DispatchOrder.created_at >= datetime.combine(d, datetime.min.time()))
        except ValueError:
            pass
    date_to = request.args.get('date_to', '').strip()
    if date_to:
        try:
            d = datetime.strptime(date_to, '%Y-%m-%d').date()
            base = base.filter(DispatchOrder.created_at <= datetime.combine(d, datetime.max.time()))
        except ValueError:
            pass
    delivery_point_id = request.args.get('delivery_point_id', type=int)
    if delivery_point_id:
        base = base.filter(DispatchOrder.delivery_point_id == delivery_point_id)
    orders = base.order_by(DispatchOrder.created_at.asc()).all()
    delivery_points = DeliveryPoint.query.filter_by(company_id=company_id, active=True).order_by(DeliveryPoint.name).all() if company_id else []
    filter_extra = [
        {'label': 'Punto', 'name': 'delivery_point_id', 'value': request.args.get('delivery_point_id', ''), 'options': [('', 'Todos')] + [(dp.id, dp.name) for dp in delivery_points]},
    ]
    return render_template(
        'dispatch_order/list_pending.html',
        orders=orders,
        title='Pedidos pendientes',
        filter_q=q,
        filter_status=status,
        filter_date_from=date_from or '',
        filter_date_to=date_to or '',
        filter_show_status=True,
        filter_status_options=[('', 'Todos'), ('pendiente', 'Pendiente'), ('en_preparacion', 'En preparación')],
        filter_extra=filter_extra,
    )


@dispatch_order_bp.route('/<int:id>')
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal', 'despachador'])
def order_detail(id):
    """Detalle de un pedido. Bodega/admin: cualquiera; despachador: solo pedidos de su punto."""
    order = ensure_company_id(id, DispatchOrder)
    if getattr(current_user, 'role', None) == 'despachador':
        point_id = getattr(current_user, 'assigned_delivery_point_id', None)
        if not point_id or order.delivery_point_id != point_id:
            from flask import abort
            abort(403)
    can_create_delivery = current_user.role in ('admin', 'super_admin', 'bodega_principal')
    return render_template('dispatch_order/detail.html', order=order, can_create_delivery=can_create_delivery, title=f'Pedido {order.order_number}')


@dispatch_order_bp.route('/<int:id>/create-delivery', methods=['POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal'])
def create_delivery_from_order(id):
    """Crear despacho desde este pedido: crea Delivery con los ítems y vincula el pedido."""
    order = ensure_company_id(id, DispatchOrder)
    if not order:
        flash('Pedido no encontrado.', 'danger')
        return redirect(url_for('dispatch_order.list_pending'))
    if order.status not in ('pendiente', 'en_preparacion'):
        flash('Solo se puede crear despacho desde un pedido pendiente o en preparación.', 'warning')
        return redirect(url_for('dispatch_order.order_detail', id=id))
    if order.delivery_id:
        flash('Este pedido ya tiene un despacho asociado.', 'warning')
        return redirect(url_for('delivery.edit_delivery', id=order.delivery_id))
    company_id = order.company_id
    warehouses = _section_warehouses(company_id)
    if not warehouses:
        flash('Configure al menos una sección del centro de acopio.', 'danger')
        return redirect(url_for('dispatch_order.order_detail', id=id))
    warehouse = order.delivery_point.warehouse if getattr(order.delivery_point, 'warehouse_id', None) else None
    if not warehouse or warehouse not in warehouses:
        warehouse = warehouses[0]
    today = datetime.utcnow().date()
    delivery = Delivery(
        company_id=company_id,
        warehouse_id=warehouse.id,
        delivery_point_id=order.delivery_point_id,
        delivery_number=_next_delivery_number(company_id),
        date=datetime.combine(today, datetime.min.time()),
        status='borrador',
        notes=order.notes or None
    )
    db.session.add(delivery)
    db.session.flush()
    for item in order.items:
        db.session.add(DeliveryItem(
            delivery_id=delivery.id,
            product_id=item.product_id,
            quantity=item.quantity
        ))
    order.delivery_id = delivery.id
    order.status = 'en_preparacion'
    db.session.commit()
    flash(f'Despacho {delivery.delivery_number} creado desde pedido {order.order_number}. Agregue ítems si desea o confirme.', 'success')
    return redirect(url_for('delivery.edit_delivery', id=delivery.id))
