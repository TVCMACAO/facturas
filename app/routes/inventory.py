from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Product, InventoryMovement, Warehouse, ProductWarehouseStock, ProductDeliveryPointStock
from app.forms import InventoryForm
from app.tenant import filter_by_company, ensure_company_id, get_current_company_id
from app.decorators import role_required
import datetime

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')

def _get_principal_warehouse():
    """Obtiene la sección por defecto: Almacén General o primera sección activa del centro de acopio."""
    company_id = get_current_company_id()
    if not company_id:
        return None
    base = Warehouse.query.filter_by(company_id=company_id, active=True)
    # Preferir Almacén General (centro de acopio)
    w = base.filter(Warehouse.warehouse_type.in_(('general', 'mayorista'))).order_by(Warehouse.name).first()
    if w:
        return w
    w = base.filter(Warehouse.warehouse_type == 'farmacia').first()
    if w:
        return w
    return base.order_by(Warehouse.name).first()

def record_inventory_movement(product, movement_type, quantity, reference_type=None, reference_id=None, notes=None):
    """
    Registra un movimiento de inventario.
    
    Args:
        product: Producto afectado
        movement_type: Tipo de movimiento ('sale', 'purchase', 'adjustment', 'return')
        quantity: Cantidad (positiva para entradas, negativa para salidas)
        reference_type: Tipo de documento relacionado ('invoice', 'quote', 'adjustment', 'credit_note')
        reference_id: ID del documento relacionado
        notes: Notas adicionales
    """
    previous_stock = product.stock
    new_stock = previous_stock + quantity
    
    movement = InventoryMovement(
        product_id=product.id,
        movement_type=movement_type,
        quantity=quantity,
        previous_stock=previous_stock,
        new_stock=new_stock,
        reference_type=reference_type,
        reference_id=reference_id,
        user_id=current_user.id if current_user.is_authenticated else None,
        notes=notes,
        created_at=datetime.datetime.utcnow()
    )
    db.session.add(movement)
    return movement

def _despachador_warehouse():
    """Para rol despachador: sección del punto asignado o primera sección del centro de acopio."""
    if not current_user.is_authenticated or getattr(current_user, 'role', None) != 'despachador':
        return None
    point = getattr(current_user, 'assigned_delivery_point', None)
    if not point or not getattr(point, 'company_id', None):
        return None
    if getattr(point, 'warehouse_id', None):
        w = Warehouse.query.filter_by(id=point.warehouse_id, active=True).first()
        if w:
            return w
    return Warehouse.query.filter(
        Warehouse.company_id == point.company_id,
        Warehouse.active == True,
        Warehouse.warehouse_type.in_(('general', 'farmacia', 'mayorista', 'minorista'))
    ).order_by(Warehouse.name).first()


@inventory_bp.route('/')
@login_required
@role_required(['user', 'admin', 'super_admin', 'bodega_principal', 'despachador'])
def list_inventory():
    q = request.args.get('q')
    stock_filter = request.args.get('stock_filter', 'all')  # 'all', 'out_of_stock', 'low_stock'
    warehouse_id = request.args.get('warehouse_id', type=int)
    company_id = get_current_company_id()
    warehouses = []
    is_despachador = getattr(current_user, 'role', None) == 'despachador'
    if company_id:
        warehouses = Warehouse.query.filter_by(company_id=company_id, active=True).order_by(Warehouse.name).all()
    if is_despachador:
        warehouse = _despachador_warehouse()
        warehouse_id = warehouse.id if warehouse else None
    elif warehouse_id:
        warehouse = next((w for w in warehouses if w.id == warehouse_id), None)
        if not warehouse:
            warehouse = _get_principal_warehouse()
    else:
        warehouse = _get_principal_warehouse()
    principal_wh = _get_principal_warehouse()

    # Construir la consulta base (filtrada por empresa)
    base_query = filter_by_company(Product.query, Product)
    query = base_query

    # Aplicar filtro de búsqueda por nombre o descripción
    if q:
        query = query.filter(
            (Product.name.like(f'%{q}%')) |
            (Product.description.like(f'%{q}%'))
        )

    products = query.order_by(Product.name).all()

    # Stock: despachador ve inventario de su almacén de entrega (punto); resto ve bodega (sección)
    delivery_point = getattr(current_user, 'assigned_delivery_point', None) if is_despachador else None
    product_stocks = []
    for product in products:
        if is_despachador and delivery_point:
            pdps = ProductDeliveryPointStock.query.filter_by(
                product_id=product.id, delivery_point_id=delivery_point.id
            ).first()
            stock_qty = pdps.quantity if pdps else 0
        elif warehouse:
            pws = ProductWarehouseStock.query.filter_by(
                product_id=product.id, warehouse_id=warehouse.id
            ).first()
            stock_qty = pws.quantity if pws else 0
        else:
            stock_qty = product.stock
        if stock_filter == 'out_of_stock' and stock_qty > 0:
            continue
        if stock_filter == 'low_stock' and (stock_qty <= 0 or stock_qty >= 5):
            continue
        product_stocks.append((product, stock_qty))

    if is_despachador and delivery_point:
        title = f'Inventario - {delivery_point.name}'
        if delivery_point.code:
            title += f' ({delivery_point.code})'
    elif warehouse:
        title = f'Inventario - {warehouse.name}'
        if warehouse.code:
            title += f' ({warehouse.code})'
    else:
        title = 'Inventario'

    filter_extra = [
        {'label': 'Bodega', 'name': 'warehouse_id', 'value': request.args.get('warehouse_id', ''), 'options': [('', 'Todas')] + [(w.id, w.name) for w in warehouses]},
        {'label': 'Stock', 'name': 'stock_filter', 'value': request.args.get('stock_filter', 'all'), 'options': [('all', 'Todos'), ('out_of_stock', 'Sin stock'), ('low_stock', 'Stock bajo (≤5)')]},
    ]
    return render_template(
        'inventory/list.html',
        product_stocks=product_stocks,
        warehouse=warehouse,
        delivery_point=delivery_point if is_despachador else None,
        warehouses=warehouses,
        warehouse_locked=is_despachador,
        title=title,
        q=q or '',
        stock_filter=stock_filter,
        principal_warehouse=principal_wh,
        filter_q=q or '',
        filter_show_dates=False,
        filter_show_status=False,
        filter_extra=filter_extra,
    )

@inventory_bp.route('/adjust/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal', 'despachador'])
def adjust_stock(id):
    product = ensure_company_id(id, Product)
    is_despachador = getattr(current_user, 'role', None) == 'despachador'
    despachador_warehouse = _despachador_warehouse() if is_despachador else None
    warehouse_id = request.args.get('warehouse_id', type=int) or request.form.get('warehouse_id', type=int)
    if is_despachador and despachador_warehouse:
        warehouse = despachador_warehouse
        if warehouse_id and warehouse_id != warehouse.id:
            flash('Solo puede ajustar stock de su bodega asignada.', 'danger')
            from app.route_tokens import url_with_token
            return redirect(url_with_token('inventory.list_inventory'))
    elif warehouse_id:
        warehouse = Warehouse.query.filter_by(
            id=warehouse_id, company_id=product.company_id, active=True
        ).first()
        if not warehouse:
            warehouse = _get_principal_warehouse()
    else:
        warehouse = _get_principal_warehouse()
    form = InventoryForm(obj=product)

    # Populate product choices for the form (only the current product)
    form.product_id.choices = [(product.id, product.name)]

    # Stock actual = en bodega principal si existe; si no, product.stock
    if warehouse:
        pws = ProductWarehouseStock.query.filter_by(
            product_id=product.id, warehouse_id=warehouse.id
        ).first()
        current_warehouse_stock = pws.quantity if pws else 0
    else:
        current_warehouse_stock = product.stock

    if form.validate_on_submit():
        new_stock = form.new_stock.data
        quantity_change = new_stock - current_warehouse_stock

        if warehouse:
            pws = ProductWarehouseStock.query.filter_by(
                product_id=product.id, warehouse_id=warehouse.id
            ).first()
            if not pws:
                pws = ProductWarehouseStock(
                    product_id=product.id,
                    warehouse_id=warehouse.id,
                    quantity=0,
                )
                db.session.add(pws)
            pws.quantity = new_stock
            # Sincronizar product.stock = suma de todas las bodegas
            new_total = sum(
                p.quantity for p in ProductWarehouseStock.query.filter_by(product_id=product.id).all()
            )
            product.stock = new_total
        else:
            product.stock = new_stock

        if quantity_change != 0:
            record_inventory_movement(
                product=product,
                movement_type='adjustment',
                quantity=quantity_change,
                reference_type='adjustment',
                reference_id=product.id,
                notes=f'Ajuste manual en bodega: {current_warehouse_stock} → {new_stock}' + (f' ({warehouse.name})' if warehouse else ''),
            )

        db.session.commit()
        flash(f'Stock de {product.name} actualizado a {new_stock} en la bodega.', 'success')
        from app.route_tokens import url_with_token
        target = url_with_token('inventory.list_inventory')
        if warehouse:
            target += ('&' if '?' in target else '?') + f'warehouse_id={warehouse.id}'
        return redirect(target)

    if not form.is_submitted():
        form.new_stock.data = current_warehouse_stock

    subtitle = f' ({warehouse.name})' if warehouse else ''
    return render_template(
        'inventory/form.html',
        form=form,
        product=product,
        warehouse=warehouse,
        current_warehouse_stock=current_warehouse_stock,
        title=f'Ajustar Stock de {product.name}{subtitle}',
    )

@inventory_bp.route('/adjust/<string:invalid_id>')
@login_required
def invalid_adjust_id(invalid_id):
    """Maneja IDs inválidos (strings) en /adjust/ y devuelve 404 después de verificar autenticación"""
    from flask import abort
    abort(404)

@inventory_bp.route('/history')
@login_required
@role_required(['user', 'admin', 'super_admin', 'bodega_principal', 'despachador'])
def all_history():
    """Muestra el historial de movimientos de todos los productos (filtrado por empresa)."""
    from sqlalchemy import or_
    base_products = filter_by_company(Product.query, Product)
    product_ids = [row[0] for row in base_products.with_entities(Product.id).all()]
    if not product_ids:
        movements = []
        base_movements = InventoryMovement.query.filter(False)
    else:
        base_movements = InventoryMovement.query.filter(InventoryMovement.product_id.in_(product_ids))
    if product_ids:
        q = request.args.get('q', '').strip()
        if q:
            product_ids_filtered = [r[0] for r in base_products.filter(
                or_(Product.code.ilike(f'%{q}%'), Product.name.ilike(f'%{q}%'))
            ).with_entities(Product.id).all()]
            if product_ids_filtered:
                base_movements = base_movements.filter(
                    or_(
                        InventoryMovement.product_id.in_(product_ids_filtered),
                        InventoryMovement.notes.ilike(f'%{q}%')
                    )
                )
            else:
                base_movements = base_movements.filter(InventoryMovement.notes.ilike(f'%{q}%'))
        movement_type = request.args.get('movement_type', '').strip()
        if movement_type:
            base_movements = base_movements.filter(InventoryMovement.movement_type == movement_type)
        date_from = request.args.get('date_from', '').strip()
        if date_from:
            try:
                d = datetime.datetime.strptime(date_from, '%Y-%m-%d').date()
                base_movements = base_movements.filter(InventoryMovement.created_at >= datetime.datetime.combine(d, datetime.datetime.min.time()))
            except ValueError:
                pass
        date_to = request.args.get('date_to', '').strip()
        if date_to:
            try:
                d = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()
                base_movements = base_movements.filter(InventoryMovement.created_at <= datetime.datetime.combine(d, datetime.datetime.max.time()))
            except ValueError:
                pass
        movements = base_movements.order_by(InventoryMovement.created_at.desc()).limit(200).all()
    filter_extra = [
        {'label': 'Tipo', 'name': 'movement_type', 'value': request.args.get('movement_type', ''), 'options': [
            ('', 'Todos'), ('sale', 'Venta'), ('purchase', 'Compra'), ('adjustment', 'Ajuste'), ('return', 'Devolución'),
            ('transfer', 'Traslado'), ('reception', 'Recepción')
        ]},
    ]
    return render_template(
        'inventory/all_history.html',
        movements=movements if product_ids else [],
        title='Historial de Inventario',
        filter_q=request.args.get('q', ''),
        filter_date_from=request.args.get('date_from', ''),
        filter_date_to=request.args.get('date_to', ''),
        filter_show_status=False,
        filter_extra=filter_extra,
    )

@inventory_bp.route('/history/<int:product_id>')
@login_required
@role_required(['user', 'admin', 'super_admin', 'bodega_principal', 'despachador'])
def product_history(product_id):
    """Muestra el historial de movimientos de un producto específico."""
    product = ensure_company_id(product_id, Product)
    movements = InventoryMovement.query.filter_by(product_id=product_id).order_by(InventoryMovement.created_at.desc()).all()
    return render_template('inventory/history.html', product=product, movements=movements, title=f'Historial de {product.name}')

@inventory_bp.route('/history/<string:invalid_id>')
@login_required
def invalid_history_id(invalid_id):
    """Maneja IDs inválidos (strings) en /history/ y devuelve 404 después de verificar autenticación"""
    from flask import abort
    abort(404)

@inventory_bp.route('/<string:invalid_id>')
@login_required
def invalid_inventory_id(invalid_id):
    """Maneja IDs inválidos (strings) y devuelve 404 después de verificar autenticación"""
    from flask import abort
    abort(404)