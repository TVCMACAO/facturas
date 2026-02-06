from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from app import db
from app.models import Product
from sqlalchemy.exc import IntegrityError
from app.forms import ProductForm
from sqlalchemy import or_

products_bp = Blueprint('products', __name__, url_prefix='/products')

@products_bp.route('/')
@login_required
def list_products():
    q = request.args.get('q')
    if q:
        products = Product.query.filter(
            or_(
                Product.code.ilike(f'%{q}%'),
                Product.name.ilike(f'%{q}%'),
                Product.description.ilike(f'%{q}%')
            )
        ).all()
    else:
        products = Product.query.all()
    return render_template('products/list.html', products=products, title='Productos', q=q)

@products_bp.route('/new', methods=['GET', 'POST'])
@login_required
def add_product():
    form = ProductForm()
    if form.validate_on_submit():
        # Generate next product code
        last_product = Product.query.order_by(Product.id.desc()).first()
        if last_product and last_product.code.startswith('HC') and last_product.code[2:].isdigit():
            next_code_number = int(last_product.code[2:]) + 1
        else:
            next_code_number = 1
        generated_code = f"HC{str(next_code_number).zfill(5)}" # Formats as HC00001, HC00002 etc.

        product = Product(
            code=generated_code, # Auto-generated code
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            stock=form.stock.data if form.stock.data is not None else 0
        )
        db.session.add(product)
        db.session.commit()
        flash('Producto añadido con éxito.', 'success')
        return redirect(url_for('products.list_products'))
    return render_template('products/form.html', form=form, title='Añadir Producto')

@products_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    form = ProductForm(obj=product)
    form.instance = product # Attach instance for validator
    if form.validate_on_submit():
        product.name = form.name.data
        product.description = form.description.data
        product.price = form.price.data
        # Validar que el stock no sea negativo
        if form.stock.data is not None and form.stock.data < 0:
            flash('El stock no puede ser negativo.', 'danger')
            return render_template('products/form.html', form=form, title='Editar Producto')
        product.stock = form.stock.data if form.stock.data is not None else product.stock
        db.session.commit()
        flash('Producto actualizado con éxito.', 'success')
        return redirect(url_for('products.list_products'))
    return render_template('products/form.html', form=form, title='Editar Producto')

@products_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    try:
        db.session.delete(product)
        db.session.commit()
        flash('Producto eliminado con éxito.', 'success')
    except IntegrityError:
        db.session.rollback() # Rollback the transaction in case of error
        flash('No se puede eliminar el producto porque está asociado a cotizaciones o facturas existentes.', 'danger')
    return redirect(url_for('products.list_products'))

@products_bp.route('/search')
@login_required
def search_products():
    """Endpoint JSON para búsqueda en tiempo real de productos"""
    q = request.args.get('q', '').strip()
    
    if not q:
        return jsonify(products=[])
    
    # Buscar en código, nombre y descripción
    product_query = Product.query.filter(
        or_(
            Product.code.ilike(f'%{q}%'),
            Product.name.ilike(f'%{q}%'),
            Product.description.ilike(f'%{q}%')
        )
    ).limit(100).all()
    
    results = []
    for product in product_query:
        stock_status = 'available'
        if product.stock <= 0:
            stock_status = 'out_of_stock'
        elif product.stock < 5:
            stock_status = 'low_stock'
        
        results.append({
            'id': product.id,
            'code': product.code,
            'name': product.name,
            'description': product.description or '',
            'price': float(product.price) if product.price else 0.0,
            'stock': product.stock,
            'stock_status': stock_status
        })
    
    return jsonify(products=results)

@products_bp.route('/<string:invalid_id>')
@login_required
def invalid_product_id(invalid_id):
    """Maneja IDs inválidos (strings) y devuelve 404 después de verificar autenticación"""
    from flask import abort
    abort(404)