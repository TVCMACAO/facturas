from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Product, InventoryMovement
from app.forms import InventoryForm
import datetime

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')

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

@inventory_bp.route('/')
@login_required
def list_inventory():
    q = request.args.get('q')
    stock_filter = request.args.get('stock_filter', 'all')  # 'all', 'out_of_stock', 'low_stock'
    
    # Construir la consulta base
    query = Product.query
    
    # Aplicar filtro de búsqueda por nombre o descripción
    if q:
        query = query.filter(
            (Product.name.like(f'%{q}%')) |
            (Product.description.like(f'%{q}%'))
        )
    
    # Aplicar filtro de stock
    if stock_filter == 'out_of_stock':
        query = query.filter(Product.stock <= 0)
    elif stock_filter == 'low_stock':
        query = query.filter(Product.stock > 0, Product.stock < 5)
    # Si es 'all', no aplicamos filtro adicional
    
    products = query.order_by(Product.name).all()
    
    return render_template('inventory/list.html', products=products, title='Inventario', q=q, stock_filter=stock_filter)

@inventory_bp.route('/adjust/<int:id>', methods=['GET', 'POST'])
@login_required
def adjust_stock(id):
    product = Product.query.get_or_404(id)
    form = InventoryForm(obj=product) # Pre-populate form with current product data
    
    # Populate product choices for the form (only the current product)
    form.product_id.choices = [(product.id, product.name)]
    
    if form.validate_on_submit():
        previous_stock = product.stock
        new_stock = form.new_stock.data
        quantity_change = new_stock - previous_stock
        
        product.stock = new_stock
        
        # Registrar movimiento de inventario
        if quantity_change != 0:
            record_inventory_movement(
                product=product,
                movement_type='adjustment',
                quantity=quantity_change,
                reference_type='adjustment',
                reference_id=product.id,
                notes=f'Ajuste manual de stock: {previous_stock} → {new_stock}'
            )
        
        db.session.commit()
        flash(f'Stock de {product.name} actualizado a {product.stock}.', 'success')
        return redirect(url_for('inventory.list_inventory'))
    
    # If GET request, pre-fill new_stock with current stock
    if not form.is_submitted():
        form.new_stock.data = product.stock

    return render_template('inventory/form.html', form=form, product=product, title=f'Ajustar Stock de {product.name}')

@inventory_bp.route('/adjust/<string:invalid_id>')
@login_required
def invalid_adjust_id(invalid_id):
    """Maneja IDs inválidos (strings) en /adjust/ y devuelve 404 después de verificar autenticación"""
    from flask import abort
    abort(404)

@inventory_bp.route('/history')
@login_required
def all_history():
    """Muestra el historial de movimientos de todos los productos."""
    movements = InventoryMovement.query.order_by(InventoryMovement.created_at.desc()).limit(100).all()
    return render_template('inventory/all_history.html', movements=movements, title='Historial de Inventario')

@inventory_bp.route('/history/<int:product_id>')
@login_required
def product_history(product_id):
    """Muestra el historial de movimientos de un producto específico."""
    product = Product.query.get_or_404(product_id)
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