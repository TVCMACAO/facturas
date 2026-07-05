# Documentación: Sistema de Validación de Stock

## Fecha: 2024

## Resumen
Este documento describe las mejoras implementadas en el sistema de gestión de inventario, incluyendo validaciones de stock, indicadores visuales y filtros de búsqueda.

---

## 1. Validación de Stock

### 1.1 Validación en Formularios de Productos

**Archivo:** `app/forms.py`

- Se agregó el campo `stock` al formulario `ProductForm` con validación `NumberRange(min=0)`
- El campo stock es obligatorio y no puede ser negativo
- Validación en backend para prevenir stock negativo al crear/editar productos

**Código:**
```python
class ProductForm(FlaskForm):
    name = StringField('Nombre del Producto', validators=[DataRequired()])
    description = TextAreaField('Descripción')
    price = FloatField('Precio', validators=[DataRequired(), NumberRange(min=0, message="El precio no puede ser negativo.")])
    stock = IntegerField('Stock Inicial', validators=[NumberRange(min=0, message="El stock no puede ser negativo.")], default=0)
    submit = SubmitField('Guardar Producto')
```

### 1.2 Validación Mejorada en Cotizaciones y Facturas

**Archivos:** `app/routes/quote.py`, `app/routes/invoice.py`

- Validación de stock disponible considerando items ya agregados en la cotización/factura
- Mensajes de error más claros indicando stock disponible vs solicitado
- Validación al editar items para prevenir stock negativo

**Lógica implementada:**
```python
# Calcular stock disponible considerando items ya agregados
available_stock = product.stock
for existing_item in quote.items:
    if existing_item.product_id == product.id:
        available_stock -= existing_item.quantity

# Validar stock disponible
if available_stock <= 0:
    flash(f'Stock agotado para {product.name}. No hay unidades disponibles.', 'danger')
elif available_stock < item_form.quantity.data:
    flash(f'Stock insuficiente para {product.name}. Stock disponible: {available_stock}, Solicitado: {item_form.quantity.data}', 'danger')
```

### 1.3 Validación en Tiempo Real (Frontend)

**Archivos:** `app/templates/quotes/view.html`, `app/templates/invoices/view.html`

- Endpoint `/products/<id>/stock` para obtener stock disponible en tiempo real
- Validación JavaScript que verifica stock disponible mientras el usuario escribe
- Deshabilita el botón de agregar si no hay stock suficiente
- Muestra advertencias visuales cuando la cantidad excede el stock

**Funcionalidades:**
- Muestra stock disponible al seleccionar un producto
- Valida cantidad mientras el usuario escribe
- Deshabilita botón si no hay stock suficiente
- Muestra advertencias visuales (rojo para agotado, amarillo para bajo)

---

## 2. Validación de Stock Agotado

### 2.1 Indicadores Visuales

**Archivo:** `app/templates/inventory/list.html`

Se implementaron indicadores visuales para productos con stock agotado o bajo:

- **Stock Agotado (0)**: 
  - Texto rojo con fondo claro
  - Icono de prohibición
  - Texto: "Agotado"
  - Clase CSS: `.stock-agotado`

- **Stock Bajo (< 5)**:
  - Texto naranja
  - Icono de advertencia
  - Texto: "X (Bajo)"
  - Clase CSS: `.stock-bajo`

**Estilos CSS:**
```css
.stock-agotado {
    color: #dc3545 !important;
    font-weight: 700;
    background-color: #ffe6e6;
    padding: 0.1rem 0.35rem;
    border-radius: 4px;
    display: inline-block;
    font-size: 0.9rem;
    line-height: 1.2;
}

.stock-bajo {
    color: #ff9800 !important;
    font-weight: 600;
    font-size: 0.9rem;
}
```

### 2.2 Validación en Backend

**Archivos:** `app/routes/quote.py`, app/routes/invoice.py`

- Validación específica para stock agotado (stock <= 0)
- Mensajes de error diferenciados:
  - "Stock agotado" cuando stock = 0
  - "Stock insuficiente" cuando stock > 0 pero insuficiente

### 2.3 Indicadores en Selector de Productos

**Archivos:** `app/templates/quotes/view.html`, `app/templates/invoices/view.html`

- Los productos con stock agotado aparecen en rojo con texto "(Stock agotado)"
- Los productos con stock bajo aparecen en naranja con texto "(Stock bajo: X)"
- Implementado usando Select2 con `templateResult`

---

## 3. Filtro de Stock

### 3.1 Select de Filtro

**Archivo:** `app/templates/inventory/list.html`

Se agregó un select para filtrar productos por estado de stock:

- **Todos los productos** (por defecto)
- **Stock agotado** (stock <= 0)
- **Stock bajo** (stock > 0 y < 5)

### 3.2 Funcionalidad Backend

**Archivo:** `app/routes/inventory.py`

```python
stock_filter = request.args.get('stock_filter', 'all')

# Aplicar filtro de stock
if stock_filter == 'out_of_stock':
    query = query.filter(Product.stock <= 0)
elif stock_filter == 'low_stock':
    query = query.filter(Product.stock > 0, Product.stock < 5)
```

### 3.3 Auto-submit

- El select tiene auto-submit: al cambiar el valor, se aplica el filtro automáticamente
- El valor seleccionado se mantiene al recargar la página
- Compatible con la búsqueda por nombre/descripción

---

## 4. Estandarización de Tamaño de Fuente

### 4.1 Regla CSS Global

**Archivo:** `app/templates/base.html`

Se agregó una regla CSS global para estandarizar el tamaño de fuente en todas las tablas:

```css
/* Estándar de tamaño de fuente para todas las tablas */
table tbody td {
    font-size: 0.9rem !important;
}

/* Estándar para campos específicos de tablas */
table tbody td .product-code,
table tbody td .product-name,
table tbody td .product-description,
table tbody td .product-price,
table tbody td .product-stock,
table tbody td .client-name,
table tbody td .client-document,
table tbody td .client-contact,
table tbody td .client-email,
table tbody td .client-phone,
table tbody td .quote-number,
table tbody td .quote-date,
table tbody td .quote-client,
table tbody td .quote-amount,
table tbody td .invoice-number,
table tbody td .invoice-date,
table tbody td .invoice-client,
table tbody td .invoice-amount {
    font-size: 0.9rem !important;
}
```

### 4.2 Aplicación en Tablas Específicas

**Archivos actualizados:**
- `app/templates/clients/list.html`
- `app/templates/products/list.html`
- `app/templates/quotes/list.html`
- `app/templates/invoices/list.html`
- `app/templates/inventory/list.html`

Todas las tablas ahora usan `font-size: 0.9rem` como estándar.

---

## 5. Endpoint de Stock en Tiempo Real

### 5.1 Endpoint

**Archivo:** `app/routes/product.py`

```python
@products_bp.route('/<int:id>/stock', methods=['GET'])
@login_required
def get_product_stock(id):
    """Endpoint para obtener el stock disponible de un producto en tiempo real"""
    quote_id = request.args.get('quote_id', type=int)
    invoice_id = request.args.get('invoice_id', type=int)
    
    product = Product.query.get_or_404(id)
    available_stock = product.stock
    
    # Si hay quote_id, restar items ya agregados en esa cotización
    if quote_id:
        from app.models import Quote, QuoteItem
        quote = Quote.query.get(quote_id)
        if quote:
            for item in quote.items:
                if item.product_id == product.id:
                    available_stock -= item.quantity
    
    # Si hay invoice_id, restar items ya agregados en esa factura
    if invoice_id:
        from app.models import Invoice, InvoiceItem
        invoice = Invoice.query.get(invoice_id)
        if invoice:
            for item in invoice.items:
                if item.product_id == product.id:
                    available_stock -= item.quantity
    
    return jsonify({
        'product_id': product.id,
        'product_name': product.name,
        'current_stock': product.stock,
        'available_stock': max(0, available_stock)
    })
```

### 5.2 Uso en Frontend

El endpoint se utiliza en JavaScript para validación en tiempo real:

```javascript
$.get('/products/' + productId + '/stock', {quote_id: quoteId}, function(stockData) {
    updateStockDisplay(stockData.available_stock);
    validateStockQuantity(quantity, stockData.available_stock);
});
```

---

## 6. Archivos Modificados

### Backend
- `app/forms.py` - Agregado campo stock al ProductForm
- `app/routes/product.py` - Endpoint de stock y manejo del campo stock
- `app/routes/quote.py` - Validación mejorada de stock
- `app/routes/invoice.py` - Validación mejorada de stock
- `app/routes/inventory.py` - Filtro de stock

### Frontend
- `app/templates/base.html` - Regla CSS global para estandarización
- `app/templates/products/form.html` - Campo stock agregado
- `app/templates/products/list.html` - Tamaño de fuente estandarizado
- `app/templates/clients/list.html` - Tamaño de fuente estandarizado
- `app/templates/quotes/list.html` - Tamaño de fuente estandarizado
- `app/templates/quotes/view.html` - Validación JavaScript en tiempo real
- `app/templates/invoices/list.html` - Tamaño de fuente estandarizado
- `app/templates/invoices/view.html` - Validación JavaScript en tiempo real
- `app/templates/inventory/list.html` - Indicadores visuales y filtro de stock

---

## 7. Beneficios

1. **Prevención de Errores**: El sistema previene operaciones con stock insuficiente o negativo
2. **Feedback Visual**: Indicadores claros del estado del stock
3. **Mejor UX**: Validación en tiempo real sin necesidad de enviar el formulario
4. **Consistencia**: Tamaño de fuente estandarizado en todas las tablas
5. **Filtrado Eficiente**: Filtro rápido para encontrar productos con problemas de stock
6. **Mantenibilidad**: Reglas CSS globales facilitan futuros cambios

---

## 8. Próximas Mejoras Sugeridas

1. Alertas automáticas cuando el stock está bajo
2. Historial de movimientos de stock más detallado
3. Reportes de stock agotado
4. Notificaciones por email cuando el stock está crítico
5. Integración con proveedores para reposición automática

---

## 9. Notas Técnicas

- El tamaño de fuente estándar es `0.9rem`
- El umbral de stock bajo es `< 5` unidades
- El stock agotado se considera cuando `stock <= 0`
- Las validaciones se realizan tanto en backend como frontend
- Se usa `!important` en CSS para asegurar que las reglas globales se apliquen

---

**Última actualización:** 2024

---

## 10. Inventario dual (limitación conocida)

El sistema maneja dos niveles de stock:

- **Ventas / cotizaciones / facturas:** usan `Product.stock` (stock global del producto por empresa).
- **Despachos, traslados y recepciones:** usan `ProductWarehouseStock` y `ProductDeliveryPointStock`.

Por tanto, el stock mostrado en cotizaciones puede no coincidir con el stock físico por bodega o punto de despacho. La unificación de ambos modelos queda planificada para una fase posterior.

