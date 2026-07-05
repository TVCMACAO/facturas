# Despachos: centro de acopio (sección) -> punto de despacho interno
import os
import re
import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_from_directory, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import (
    Delivery, DeliveryItem, DeliveryEvidence,
    Warehouse, DeliveryPoint, ProductWarehouseStock, ProductDeliveryPointStock, Product, InventoryMovement,
    DispatchOrder
)
from app.forms import DeliveryForm, DeliveryConfirmForm
from app.tenant import filter_by_company, ensure_company_id, get_current_company_id
from app.decorators import role_required, log_audit
from datetime import datetime
from sqlalchemy import or_

delivery_bp = Blueprint('delivery', __name__, url_prefix='/delivery')

SECTION_TYPES = ('general', 'farmacia', 'mayorista')


def _section_warehouses(company_id):
    """Secciones del centro de acopio para despachos (origen)."""
    return Warehouse.query.filter(
        Warehouse.company_id == company_id,
        Warehouse.active == True,
        Warehouse.warehouse_type.in_(SECTION_TYPES)
    ).order_by(Warehouse.name).all()


def _next_delivery_number(company_id):
    last = Delivery.query.filter_by(company_id=company_id).order_by(Delivery.id.desc()).first()
    n = (int(last.delivery_number.replace('PRE-', '')) + 1) if (last and last.delivery_number and last.delivery_number.startswith('PRE-')) else 1
    return f'PRE-{n:05d}'


@delivery_bp.route('/')
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal'])
def list_deliveries():
    company_id = get_current_company_id()
    base = filter_by_company(Delivery.query, Delivery)
    q = request.args.get('q', '').strip()
    if q:
        base = base.filter(Delivery.delivery_number.ilike(f'%{q}%'))
    status = request.args.get('status', '').strip()
    if status:
        base = base.filter(Delivery.status == status)
    date_from = request.args.get('date_from', '').strip()
    if date_from:
        try:
            d = datetime.strptime(date_from, '%Y-%m-%d').date()
            base = base.filter(Delivery.date >= datetime.combine(d, datetime.min.time()))
        except ValueError:
            pass
    date_to = request.args.get('date_to', '').strip()
    if date_to:
        try:
            d = datetime.strptime(date_to, '%Y-%m-%d').date()
            base = base.filter(Delivery.date <= datetime.combine(d, datetime.max.time()))
        except ValueError:
            pass
    warehouse_id = request.args.get('warehouse_id', type=int)
    if warehouse_id:
        base = base.filter(Delivery.warehouse_id == warehouse_id)
    delivery_point_id = request.args.get('delivery_point_id', type=int)
    if delivery_point_id:
        base = base.filter(Delivery.delivery_point_id == delivery_point_id)
    deliveries = base.order_by(Delivery.date.desc(), Delivery.id.desc()).all()
    warehouses = _section_warehouses(company_id) if company_id else []
    delivery_points = DeliveryPoint.query.filter_by(company_id=company_id, active=True).order_by(DeliveryPoint.name).all() if company_id else []
    filter_extra = [
        {'label': 'Sección', 'name': 'warehouse_id', 'value': request.args.get('warehouse_id', ''), 'options': [('', 'Todas')] + [(w.id, w.name) for w in warehouses]},
        {'label': 'Punto', 'name': 'delivery_point_id', 'value': request.args.get('delivery_point_id', ''), 'options': [('', 'Todos')] + [(dp.id, dp.name) for dp in delivery_points]},
    ]
    return render_template(
        'delivery/list.html',
        deliveries=deliveries,
        title='Despachos',
        filter_q=q,
        filter_status=status,
        filter_date_from=date_from or '',
        filter_date_to=date_to or '',
        filter_show_status=True,
        filter_status_options=[('', 'Todos'), ('borrador', 'Borrador'), ('confirmado', 'Confirmado'), ('anulado', 'Anulado')],
        filter_extra=filter_extra,
    )


def _despachador_warehouse_and_point():
    """Para rol despachador: devuelve (warehouse, delivery_point) o (None, None)."""
    if not current_user.is_authenticated or getattr(current_user, 'role', None) != 'despachador':
        return None, None
    point = getattr(current_user, 'assigned_delivery_point', None)
    if not point:
        return None, None
    warehouse = point.warehouse if getattr(point, 'warehouse_id', None) else None
    if not warehouse and point.company_id:
        warehouses = Warehouse.query.filter(
            Warehouse.company_id == point.company_id,
            Warehouse.active == True,
            Warehouse.warehouse_type.in_(SECTION_TYPES + ('minorista',))
        ).order_by(Warehouse.name).limit(1).all()
        warehouse = warehouses[0] if warehouses else None
    return warehouse, point


@delivery_bp.route('/tablet')
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal', 'despachador'])
def tablet_view():
    """Vista simplificada para tablet vertical. Despachador: solo su almacén; admin/bodega: lista general."""
    is_despachador = getattr(current_user, 'role', None) == 'despachador'
    delivery_point = None
    warehouse = None
    if is_despachador:
        warehouse, delivery_point = _despachador_warehouse_and_point()
        if not delivery_point:
            flash('No tiene punto de despacho asignado. Contacte al administrador.', 'warning')
            return redirect(url_for('main.index'))
        base = Delivery.query.filter_by(company_id=current_user.company_id, delivery_point_id=delivery_point.id)
        deliveries = base.order_by(Delivery.date.desc(), Delivery.id.desc()).limit(50).all()
    else:
        base = filter_by_company(Delivery.query, Delivery)
        deliveries = base.order_by(Delivery.date.desc(), Delivery.id.desc()).limit(50).all()
    return render_template('delivery/tablet.html', deliveries=deliveries, is_despachador=is_despachador,
                           delivery_point=delivery_point, warehouse=warehouse, title='Despachos - Tablet')


@delivery_bp.route('/tablet/start', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal', 'despachador'])
def tablet_start():
    """Crea un despacho e redirige a edición tablet. Despachador: usa bodega del punto asignado."""
    company_id = get_current_company_id()
    if not company_id:
        flash('No tiene empresa asignada.', 'danger')
        return redirect(url_for('delivery.tablet_view'))
    warehouse = None
    delivery_point = None
    if getattr(current_user, 'role', None) == 'despachador':
        warehouse, delivery_point = _despachador_warehouse_and_point()
        if not delivery_point:
            flash('No tiene punto de despacho asignado.', 'warning')
            return redirect(url_for('delivery.tablet_view'))
        if not warehouse:
            flash('El punto de despacho no tiene sección por defecto. Configure en Administración.', 'warning')
            return redirect(url_for('delivery.tablet_view'))
    else:
        warehouses = _section_warehouses(company_id)
        delivery_points = DeliveryPoint.query.filter_by(company_id=company_id, active=True).order_by(DeliveryPoint.name).all()
        if len(warehouses) == 1 and len(delivery_points) == 1:
            warehouse, delivery_point = warehouses[0], delivery_points[0]
            if delivery_point.warehouse_id:
                warehouse = Warehouse.query.get(delivery_point.warehouse_id) or warehouse
        else:
            return redirect(url_for('delivery.create_delivery'))
    today = datetime.utcnow().date()
    d = Delivery(
        company_id=company_id,
        warehouse_id=warehouse.id,
        delivery_point_id=delivery_point.id,
        delivery_number=_next_delivery_number(company_id),
        date=datetime.combine(today, datetime.min.time()),
        status='borrador',
        notes=None
    )
    db.session.add(d)
    db.session.commit()
    flash(f'Despacho {d.delivery_number} creado. Agregue ítems.', 'success')
    return redirect(url_for('delivery.tablet_dispatch', id=d.id))


@delivery_bp.route('/tablet/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal', 'despachador'])
def tablet_dispatch(id):
    """Vista tablet para agregar ítems y confirmar. Despachador solo ve despachos de su punto."""
    delivery = _get_delivery(id)
    if getattr(current_user, 'role', None) == 'despachador':
        if not current_user.assigned_delivery_point_id or delivery.delivery_point_id != current_user.assigned_delivery_point_id:
            flash('No puede editar este despacho.', 'danger')
            return redirect(url_for('delivery.tablet_view'))
    if delivery.status != 'borrador':
        return redirect(url_for('delivery.view_delivery', id=id))
    company_id = delivery.company_id
    products = Product.query.filter_by(company_id=company_id).order_by(Product.name).all()
    is_despachador = getattr(current_user, 'role', None) == 'despachador'
    return render_template('delivery/tablet_dispatch.html', delivery=delivery, products=products, is_despachador=is_despachador, title=f'Despacho {delivery.delivery_number}')


@delivery_bp.route('/product-lookup')
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal', 'despachador'])
def product_lookup():
    """API: buscar producto por código, nombre o código de barras. Si 'by' no se envía o es 'auto', busca en los tres automáticamente."""
    q = request.args.get('q', '').strip()
    by = request.args.get('by', 'auto').lower()  # auto | code | name | barcode
    warehouse_id = request.args.get('warehouse_id', type=int)
    delivery_point_id = request.args.get('delivery_point_id', type=int)  # para despachador: stock en su punto
    company_id = get_current_company_id()
    if not company_id or not q:
        return jsonify(products=[])
    base = Product.query.filter_by(company_id=company_id)
    pattern = f'%{q}%'
    if by == 'barcode':
        base = base.filter(Product.barcode.ilike(pattern))
    elif by == 'name':
        base = base.filter(Product.name.ilike(pattern))
    elif by == 'code':
        base = base.filter(Product.code.ilike(pattern))
    else:
        # auto: buscar en código, nombre y código de barras a la vez
        base = base.filter(or_(
            Product.code.ilike(pattern),
            Product.name.ilike(pattern),
            Product.barcode.ilike(pattern),
        ))
    products = base.limit(20).all()
    result = []
    for p in products:
        stock_in_warehouse = None
        stock_at_point = None
        if delivery_point_id:
            pdps = ProductDeliveryPointStock.query.filter_by(product_id=p.id, delivery_point_id=delivery_point_id).first()
            stock_at_point = pdps.quantity if pdps else 0
        if warehouse_id:
            pws = ProductWarehouseStock.query.filter_by(product_id=p.id, warehouse_id=warehouse_id).first()
            stock_in_warehouse = pws.quantity if pws else 0
        result.append({
            'id': p.id,
            'code': p.code,
            'name': p.name,
            'barcode': p.barcode or '',
            'unit_of_sale': p.unit_of_sale or 'unidad',
            'units_per_package': p.units_per_package,
            'stock': p.stock,
            'stock_in_warehouse': stock_in_warehouse,
            'stock_at_point': stock_at_point,
            'price': float(p.price) if p.price else 0,
        })
    return jsonify(products=result)


# Palabras de encabezado del documento que no deben usarse como nombre del receptor
_OCR_NAME_BLACKLIST = (
    'identificacion', 'identificación', 'personal', 'cedula', 'cédula', 'ciudadania', 'ciudadanía',
    'republica', 'república', 'colombia', 'documento', 'carnet', 'persona', 'empleado', 'portador',
    'intransferible', 'comuniquese', 'emergencia', 'lider', 'sistema', 'redes', 'clinica', 'maicao',
)

def _ocr_is_name_noise(line):
    """Devuelve True si la línea parece texto de encabezado del documento, no un nombre de persona."""
    if not line or len(line) < 3:
        return True
    low = line.lower().strip()
    for word in _OCR_NAME_BLACKLIST:
        if word in low:
            return True
    return False


# Fragmentos de 1–2 caracteres que el OCR suele añadir por firma/fondo (quitar del nombre)
_OCR_NAME_TOKEN_NOISE = frozenset(['is', 'fe', 'ex', 'es', 'j', 'ad', 'id', 'ip'])


def _ocr_clean_name_tokens(name):
    """Quita del nombre tokens de ruido OCR (ej. 'é', 'i', 'is') que no están en la cédula. Salida: 'MELENDRES ACOSTA DEINER'."""
    if not name or not name.strip():
        return name
    tokens = name.split()
    kept = []
    for t in tokens:
        if len(t) == 1:  # quitar "é", "i", "j", etc.
            continue
        if len(t) == 2 and t.lower() in _OCR_NAME_TOKEN_NOISE:  # quitar "is", "fe", "ex", etc.
            continue
        if not re.match(r'^[A-Za-zÁáÉéÍíÓóÚúÑñ\-]+$', t):  # solo letras y guión
            continue
        kept.append(t)
    return ' '.join(kept).strip()[:120]


def _ocr_validate_doc_number(num_str):
    """Devuelve (normalized, type) si es válido; si no, (None, None). Solo dígitos, longitud 5-15."""
    num = re.sub(r'[\s\.\-]', '', num_str)
    if not num or not num.isdigit() or len(num) < 5 or len(num) > 15:
        return None, None
    # 5-10 dígitos: Cédula (CC); 11+ dígitos: NIT
    return num, ('nit' if len(num) > 10 else 'cedula')


def _ocr_carnet_extract(text):
    """Extrae nombre (una sola línea: apellidos + nombres) y número de documento. Solo con etiquetas explícitas."""
    result = {'recipient_name': '', 'recipient_document_number': '', 'document_type': ''}
    if not text or not text.strip():
        return result
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # --- Documento: solo si hay etiqueta explícita (orden de prioridad) ---
    patterns_doc = [
        (r'cc\s*[\s:.\-]*(\d[\d.\s\-]*)', re.IGNORECASE),
        (r'(?:numero|n[uú]mero)\s*[\s:]*(\d[\d.\s\-]*)', re.IGNORECASE),
        (r'(?:cedula|cédula|documento|nit|identificaci[oó]n|dni)\s*[\s:]*(\d[\d.\s\-]*)', re.IGNORECASE),
    ]
    doc_matched_raw = None
    for pat, flags in patterns_doc:
        m = re.search(pat, text, flags)
        if m:
            raw = m.group(1)
            num, doc_type = _ocr_validate_doc_number(raw)
            if num:
                result['recipient_document_number'] = num
                result['document_type'] = doc_type
                break
            doc_matched_raw = raw
    # Fallback: si no hay etiqueta pero hay nombre, buscar cualquier número 5-15 dígitos en el texto
    if not result['recipient_document_number'] and lines:
        for chunk in re.findall(r'\d[\d.\s\-]{4,14}', text):
            num, doc_type = _ocr_validate_doc_number(chunk)
            if num:
                result['recipient_document_number'] = num
                result['document_type'] = doc_type
                break

    # --- Nombre: solo desde NOMBRES/APELLIDOS o Nombre completo. Una sola línea concatenada. ---
    nombres_val = apellidos_val = nombre_completo_val = ''

    def _valid_name(s, max_words=8):
        if not s or len(s) < 4 or _ocr_is_name_noise(s):
            return False
        if any(c.isdigit() for c in s):
            return False
        letters = re.sub(r'[^A-Za-zÁáÉéÍíÓóÚúÑñ\s]', '', s)
        if len(letters) < len(s) * 0.7:
            return False
        return 1 <= len(s.split()) <= max_words

    for i, line in enumerate(lines):
        if re.match(r'^nombres?\s*:?\s*$', line, re.IGNORECASE) and i + 1 < len(lines):
            next_ln = lines[i + 1].strip()[:80]
            if _valid_name(next_ln):
                nombres_val = next_ln
        elif re.match(r'^nombres?\s*:', line, re.IGNORECASE):
            val = re.sub(r'^nombres?\s*:\s*', '', line, flags=re.IGNORECASE).strip()[:80]
            if _valid_name(val):
                nombres_val = val
        elif re.match(r'^apellidos?\s*:?\s*$', line, re.IGNORECASE) and i + 1 < len(lines):
            next_ln = lines[i + 1].strip()[:80]
            if _valid_name(next_ln):
                apellidos_val = next_ln
        elif re.match(r'^apellidos?\s*:', line, re.IGNORECASE):
            val = re.sub(r'^apellidos?\s*:\s*', '', line, flags=re.IGNORECASE).strip()[:80]
            if _valid_name(val):
                apellidos_val = val
        elif re.match(r'^nombre\s+completo\s*:', line, re.IGNORECASE):
            val = re.sub(r'^nombre\s+completo\s*:\s*', '', line, flags=re.IGNORECASE).strip()[:120]
            if _valid_name(val):
                nombre_completo_val = val
        elif re.match(r'^(?:nombre|name)\s*:', line, re.IGNORECASE):
            val = re.sub(r'^(?:nombre|name)\s*:\s*', '', line, flags=re.IGNORECASE).strip()[:120]
            if _valid_name(val):
                nombre_completo_val = val

    if nombre_completo_val:
        result['recipient_name'] = nombre_completo_val[:120]
    elif apellidos_val or nombres_val:
        result['recipient_name'] = (' '.join([apellidos_val, nombres_val]).strip())[:120]
    else:
        # Fallback carné sin etiquetas: dos líneas consecutivas que parecen nombre (2–4 palabras, solo letras, no blacklist)
        for i in range(len(lines) - 1):
            a, b = lines[i].strip()[:80], lines[i + 1].strip()[:80]
            if not a or not b:
                continue
            if _valid_name(a, max_words=4) and _valid_name(b, max_words=4):
                combined = (a + ' ' + b).strip()[:120]
                if combined and not _ocr_is_name_noise(combined):
                    result['recipient_name'] = combined
                    break
        # Fallback una sola línea: nombre junto (ej. HEMMISCAMILO) o con puntos
        if not result['recipient_name']:
            best = ''
            for line in lines:
                line = line.strip()[:80]
                if not line or len(line) < 6 or any(c.isdigit() for c in line) or _ocr_is_name_noise(line):
                    continue
                letters = re.sub(r'[^A-Za-zÁáÉéÍíÓóÚúÑñ\s]', '', line)
                if len(letters) < len(line) * 0.6:
                    continue
                tokens = re.split(r'[\s.]+', line)
                if 1 <= len(tokens) <= 6 and len(line) > len(best):
                    best = line
            if best:
                cleaned = re.sub(r'\.', ' ', best).strip()
                cleaned = re.sub(r'\s+', ' ', cleaned)
                # Partir nombre junto: HEMMISCAMILO → HEMMIS CAMILO
                cleaned = re.sub(r'([a-záéíóúñ])([A-ZÁÉÍÓÚÑ])', r'\1 \2', cleaned)
                cleaned = re.sub(r'(?<=[A-ZÁÉÍÓÚÑ])(?=[A-ZÁÉÍÓÚÑ][a-záéíóúñ])', ' ', cleaned)
                # Si queda una palabra todo mayúsculas larga (ej. HEMMISCAMILO), partir por la mitad
                words = cleaned.split()
                out = []
                for w in words:
                    if len(w) >= 8 and w.isupper() and re.match(r'^[A-ZÁÉÍÓÚÑ]+$', w):
                        mid = len(w) // 2
                        out.append(w[:mid])
                        out.append(w[mid:])
                    else:
                        out.append(w)
                result['recipient_name'] = ' '.join(out).strip()[:120]
    # No devolver nombre si parece basura OCR; si se rechaza, intentar versión "limpia" para que el usuario pueda editar
    if result['recipient_name']:
        n = result['recipient_name']
        garbage_chars = r"[\d\'\"\`\u2018\u2019\u201a\u201b]"
        letters_only = re.sub(r'[^A-Za-zÁáÉéÍíÓóÚúÑñ\s]', '', n)
        if re.search(garbage_chars, n) or len(letters_only) < len(n) * 0.82:
            cleaned = re.sub(garbage_chars, ' ', n)
            cleaned = re.sub(r'[\s\-]+', ' ', cleaned).strip()
            cleaned = re.sub(r'[\s\-]+$', '', cleaned)
            if len(cleaned) >= 6:
                lonly = re.sub(r'[^A-Za-zÁáÉéÍíÓóÚúÑñ\s]', '', cleaned)
                if len(lonly) >= len(cleaned) * 0.6:
                    result['recipient_name'] = cleaned[:120]
                else:
                    result['recipient_name'] = ''
            else:
                result['recipient_name'] = ''
    # Quitar fragmentos de ruido OCR (firma, fondo): "é", "i", "is", etc.
    if result['recipient_name']:
        result['recipient_name'] = _ocr_clean_name_tokens(result['recipient_name'])
    return result


@delivery_bp.route('/ocr-carnet', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal', 'despachador'])
def ocr_carnet():
    """Recibe imagen del carnet (POST), ejecuta OCR y devuelve nombre y número de documento. GET devuelve mensaje."""
    if request.method == 'GET':
        return jsonify(error='Esta URL debe usarse con POST enviando una imagen (campo file). Use el botón "Leer carnet con cámara" en Confirmar entrega.'), 200
    from flask_wtf.csrf import validate_csrf
    try:
        validate_csrf(request.form.get('csrf_token'))
    except Exception:
        return jsonify(error='Token de seguridad inválido'), 400
    if 'file' not in request.files:
        return jsonify(error='No se envió ninguna imagen'), 400
    f = request.files['file']
    if not f or not f.filename:
        return jsonify(error='Archivo vacío'), 400
    allowed = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
    fn_lower = (f.filename or '').lower()
    ct_lower = (f.content_type or '').lower()
    if 'heic' in fn_lower or 'heic' in ct_lower:
        return jsonify(error='Formato no soportado. Use JPEG o PNG.'), 400
    if f.content_type and f.content_type not in allowed:
        return jsonify(error='Solo se permiten imágenes (JPEG, PNG, GIF, WebP)'), 400
    try:
        import pytesseract
        from PIL import Image, ImageOps
    except ImportError as ie:
        return jsonify(error='OCR no disponible. Ejecute en el servidor: pip install Pillow pytesseract'), 503
    # Ruta a Tesseract en el PC del servidor (no en la tablet)
    _default_win = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    _tesseract_cmd = (current_app.config.get('TESSERACT_CMD') or os.environ.get('TESSERACT_CMD', '') or '').strip()
    if _tesseract_cmd:
        _tesseract_cmd = os.path.normpath(_tesseract_cmd.replace('/', os.sep))
    if not _tesseract_cmd or not os.path.isfile(_tesseract_cmd):
        if os.path.isfile(_default_win):
            _tesseract_cmd = _default_win
    if _tesseract_cmd and os.path.isfile(_tesseract_cmd):
        pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd
    else:
        return jsonify(error='Tesseract no encontrado. Instale en el PC del servidor desde https://github.com/UB-Mannheim/tesseract/wiki'), 503
    try:
        img = Image.open(f)
        img = ImageOps.exif_transpose(img)
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        w, h = img.size
        # Precisión para fotos desde tablet: redimensionar si es pequeño, limitar tamaño máximo
        if w < 600 or h < 400:
            scale = max(600 / w, 400 / h, 1.5)
            new_w, new_h = int(w * scale), int(h * scale)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            w, h = img.size
        max_side = 1400
        if max(w, h) > max_side:
            ratio = max_side / max(w, h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)
        img = img.convert('L')
        try:
            from PIL import ImageEnhance
            img = ImageEnhance.Contrast(img).enhance(1.3)
            img = ImageEnhance.Sharpness(img).enhance(1.5)
        except Exception:
            try:
                from PIL import ImageEnhance
                img = ImageEnhance.Contrast(img).enhance(1.2)
            except Exception:
                pass
        psm_config = '--psm 6'
        try:
            text = pytesseract.image_to_string(img, lang='spa', config=psm_config) or ''
        except Exception as lang_err:
            err_lower = str(lang_err).lower()
            if 'spa' in err_lower or 'language' in err_lower or 'datapath' in err_lower:
                text = pytesseract.image_to_string(img, lang='eng', config=psm_config) or ''
            else:
                raise
        if not (text and len(text.strip()) > 10):
            text = pytesseract.image_to_string(img, lang='eng', config=psm_config) or ''
        if not (text and len(text.strip()) > 30):
            for alt_psm in ('--psm 4', '--psm 13'):
                try:
                    t2 = pytesseract.image_to_string(img, lang='spa', config=alt_psm) or ''
                    if len(t2.strip()) > len((text or '').strip()):
                        text = t2
                except Exception:
                    pass
    except Exception as e:
        err_msg = str(e).lower()
        if 'tesseract' in err_msg or 'not found' in err_msg or 'no such file' in err_msg:
            return jsonify(error=f'Tesseract: {str(e)}. Compruebe la ruta en .env (TESSERACT_CMD).'), 503
        return jsonify(error=f'Error al procesar la imagen: {str(e)}'), 500
    data = _ocr_carnet_extract(text)
    _debug_mode = request.args.get('debug') == '1' or (os.environ.get('OCR_DEBUG') or '').strip() in ('1', 'true', 'yes')
    if _debug_mode:
        data['ocr_text_length'] = len(text.strip()) if text else 0
        _preview = (text or '').strip().replace('\n', ' ').replace('\r', '')[:200]
        data['ocr_preview'] = _preview
    return jsonify(data)


@delivery_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal'])
def create_delivery():
    company_id = get_current_company_id()
    if not company_id:
        flash('No tiene empresa asignada.', 'danger')
        return redirect(url_for('delivery.list_deliveries'))
    warehouses = _section_warehouses(company_id)
    delivery_points = DeliveryPoint.query.filter_by(company_id=company_id, active=True).order_by(DeliveryPoint.name).all()
    if not warehouses or not delivery_points:
        flash('Configure al menos una sección del centro de acopio y un punto de despacho.', 'warning')
        return redirect(url_for('delivery.list_deliveries'))
    # Si solo hay una bodega y un almacén de entrega, crear despacho directo y ir a agregar ítems
    if len(warehouses) == 1 and len(delivery_points) == 1:
        today = datetime.utcnow().date()
        d = Delivery(
            company_id=company_id,
            warehouse_id=warehouses[0].id,
            delivery_point_id=delivery_points[0].id,
            delivery_number=_next_delivery_number(company_id),
            date=datetime.combine(today, datetime.min.time()),
            status='borrador',
            notes=None
        )
        db.session.add(d)
        db.session.commit()
        flash(f'Despacho {d.delivery_number} creado. Agregue ítems.', 'success')
        return redirect(url_for('delivery.edit_delivery', id=d.id))
    form = DeliveryForm()
    form.warehouse_id.choices = [(w.id, w.name) for w in warehouses]
    form.delivery_point_id.choices = [(dp.id, dp.name) for dp in delivery_points]
    today = datetime.utcnow().date()
    form.date.data = today
    if form.validate_on_submit():
        d = Delivery(
            company_id=company_id,
            warehouse_id=form.warehouse_id.data,
            delivery_point_id=form.delivery_point_id.data,
            delivery_number=_next_delivery_number(company_id),
            date=datetime.combine(today, datetime.min.time()),
            status='borrador',
            notes=form.notes.data
        )
        db.session.add(d)
        db.session.commit()
        flash(f'Despacho {d.delivery_number} creado. Agregue ítems.', 'success')
        return redirect(url_for('delivery.edit_delivery', id=d.id))
    return render_template('delivery/form.html', form=form, delivery=None, title='Nuevo Despacho')


def _get_delivery(id):
    return ensure_company_id(id, Delivery)


def _despachador_can_access(delivery):
    """True si el usuario actual puede acceder al despacho (despachador: solo su punto)."""
    if getattr(current_user, 'role', None) != 'despachador':
        return True
    return current_user.assigned_delivery_point_id == delivery.delivery_point_id


@delivery_bp.route('/<int:id>')
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal', 'despachador'])
def view_delivery(id):
    delivery = _get_delivery(id)
    if not _despachador_can_access(delivery):
        flash('No puede ver este despacho.', 'danger')
        return redirect(url_for('delivery.tablet_view'))
    # URL para el formulario "Completar receptor" (construida sin url_for para evitar BuildError si el endpoint no está registrado en este proceso)
    from app.route_tokens import generate_route_token
    update_recipient_path = f"/delivery/{delivery.id}/update-recipient"
    if current_user.is_authenticated:
        token = generate_route_token(update_recipient_path)
        update_recipient_url = f"{update_recipient_path}?token={token}"
    else:
        update_recipient_url = update_recipient_path
    return render_template('delivery/detail.html', delivery=delivery, update_recipient_url=update_recipient_url, title=f'Despacho {delivery.delivery_number}')


@delivery_bp.route('/<int:id>/update-recipient', methods=['POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal', 'despachador'])
def update_recipient(id):
    """Completar o corregir datos del receptor en un despacho ya confirmado."""
    delivery = _get_delivery(id)
    if not _despachador_can_access(delivery):
        flash('No puede editar este despacho.', 'danger')
        return redirect(url_for('delivery.tablet_view'))
    if delivery.status != 'confirmado':
        flash('Solo se pueden completar datos del receptor en despachos confirmados.', 'warning')
        return redirect(url_for('delivery.view_delivery', id=id))
    from flask_wtf.csrf import validate_csrf
    try:
        validate_csrf(request.form.get('csrf_token'))
    except Exception:
        flash('Token de seguridad inválido.', 'danger')
        return redirect(url_for('delivery.view_delivery', id=id))
    delivery.recipient_name = (request.form.get('recipient_name') or '').strip() or None
    delivery.recipient_document_number = (request.form.get('recipient_document_number') or '').strip() or None
    delivery.recipient_document_type = (request.form.get('recipient_document_type') or '').strip() or None
    if delivery.recipient_document_type and delivery.recipient_document_type not in ('cedula', 'nit'):
        delivery.recipient_document_type = None
    db.session.commit()
    flash('Datos del receptor actualizados.', 'success')
    return redirect(url_for('delivery.view_delivery', id=id))


@delivery_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal', 'despachador'])
def edit_delivery(id):
    delivery = _get_delivery(id)
    if not _despachador_can_access(delivery):
        flash('No puede editar este despacho.', 'danger')
        return redirect(url_for('delivery.tablet_view'))
    if delivery.status != 'borrador':
        flash('Solo se pueden editar despachos en borrador.', 'warning')
        return redirect(url_for('delivery.view_delivery', id=id))
    company_id = delivery.company_id
    warehouses = _section_warehouses(company_id)
    delivery_points = DeliveryPoint.query.filter_by(company_id=company_id, active=True).all()
    form = DeliveryForm()
    form.warehouse_id.choices = [(w.id, w.name) for w in warehouses]
    form.delivery_point_id.choices = [(dp.id, dp.name) for dp in delivery_points]
    if form.validate_on_submit():
        delivery.warehouse_id = form.warehouse_id.data
        delivery.delivery_point_id = form.delivery_point_id.data
        # La fecha no se edita: se mantiene la original del despacho
        delivery.notes = form.notes.data
        db.session.commit()
        flash('Despacho actualizado.', 'success')
        return redirect(url_for('delivery.edit_delivery', id=id))
    if request.method == 'GET':
        form.warehouse_id.data = delivery.warehouse_id
        form.delivery_point_id.data = delivery.delivery_point_id
        form.date.data = delivery.date.date() if delivery.date else datetime.utcnow().date()
        form.notes.data = delivery.notes
    warehouses = _section_warehouses(company_id)
    delivery_points = DeliveryPoint.query.filter_by(company_id=company_id, active=True).all()
    single_warehouse_and_point = (len(warehouses) == 1 and len(delivery_points) == 1)
    products = Product.query.filter_by(company_id=company_id).order_by(Product.name).all()
    return render_template('delivery/edit.html', delivery=delivery, form=form, products=products, single_warehouse_and_point=single_warehouse_and_point, title=f'Editar {delivery.delivery_number}')


@delivery_bp.route('/<int:id>/add-item', methods=['POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal', 'despachador'])
def add_delivery_item(id):
    delivery = _get_delivery(id)
    if not _despachador_can_access(delivery):
        flash('No puede modificar este despacho.', 'danger')
        return redirect(url_for('delivery.tablet_view'))
    if delivery.status != 'borrador':
        flash('Solo se pueden agregar ítems a despachos en borrador.', 'warning')
        return redirect(url_for('delivery.edit_delivery', id=id))
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', type=int)
    if not product_id or not quantity or quantity < 1:
        flash('Producto y cantidad requeridos.', 'danger')
        _redirect_after_item = url_for('delivery.tablet_dispatch', id=id) if getattr(current_user, 'role', None) == 'despachador' else url_for('delivery.edit_delivery', id=id)
        return redirect(_redirect_after_item)
    product = Product.query.filter_by(id=product_id, company_id=delivery.company_id).first_or_404()
    is_despachador = getattr(current_user, 'role', None) == 'despachador'
    if is_despachador:
        pdps = ProductDeliveryPointStock.query.filter_by(product_id=product_id, delivery_point_id=delivery.delivery_point_id).first()
        available = (pdps.quantity if pdps else 0)
        stock_msg = 'en su almacén de entrega'
    else:
        pws = ProductWarehouseStock.query.filter_by(product_id=product_id, warehouse_id=delivery.warehouse_id).first()
        available = (pws.quantity if pws else 0)
        stock_msg = 'en bodega'
    existing = sum(i.quantity for i in delivery.items if i.product_id == product_id)
    available -= existing
    if quantity > available:
        flash(f'Stock insuficiente {stock_msg} para {product.name}. Disponible: {available}. Solicite al centro de acopio si lo necesita.', 'danger' if is_despachador else 'danger')
        _redirect_after_item = url_for('delivery.tablet_dispatch', id=id) if is_despachador else url_for('delivery.edit_delivery', id=id)
        return redirect(_redirect_after_item)
    existing_item = next((i for i in delivery.items if i.product_id == product_id), None)
    if existing_item:
        existing_item.quantity += quantity
    else:
        delivery.items.append(DeliveryItem(product_id=product_id, quantity=quantity))
    db.session.commit()
    flash(f'Ítem agregado: {product.name} x {quantity}', 'success')
    _redirect_after_item = url_for('delivery.tablet_dispatch', id=id) if getattr(current_user, 'role', None) == 'despachador' else url_for('delivery.edit_delivery', id=id)
    return redirect(_redirect_after_item)


@delivery_bp.route('/<int:id>/remove-item/<int:item_id>', methods=['POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal', 'despachador'])
def remove_delivery_item(id, item_id):
    delivery = _get_delivery(id)
    if not _despachador_can_access(delivery):
        flash('No puede modificar este despacho.', 'danger')
        return redirect(url_for('delivery.tablet_view'))
    if delivery.status != 'borrador':
        flash('Solo se pueden quitar ítems de despachos en borrador.', 'warning')
        return redirect(url_for('delivery.edit_delivery', id=id))
    item = DeliveryItem.query.filter_by(id=item_id, delivery_id=id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash('Ítem quitado.', 'success')
    if getattr(current_user, 'role', None) == 'despachador':
        return redirect(url_for('delivery.tablet_dispatch', id=id))
    return redirect(url_for('delivery.edit_delivery', id=id))


@delivery_bp.route('/<int:id>/update-item/<int:item_id>', methods=['POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal', 'despachador'])
def update_delivery_item(id, item_id):
    """Actualizar cantidad de un ítem del despacho (mismo flujo que en despachos)."""
    delivery = _get_delivery(id)
    if not _despachador_can_access(delivery):
        flash('No puede modificar este despacho.', 'danger')
        return redirect(url_for('delivery.tablet_view'))
    if delivery.status != 'borrador':
        flash('Solo se pueden editar ítems en despachos en borrador.', 'warning')
        _r = url_for('delivery.tablet_dispatch', id=id) if getattr(current_user, 'role', None) == 'despachador' else url_for('delivery.edit_delivery', id=id)
        return redirect(_r)
    item = DeliveryItem.query.filter_by(id=item_id, delivery_id=id).first_or_404()
    quantity = request.form.get('quantity', type=int)
    if not quantity or quantity < 1:
        flash('Cantidad debe ser al menos 1.', 'danger')
        _r = url_for('delivery.tablet_dispatch', id=id) if getattr(current_user, 'role', None) == 'despachador' else url_for('delivery.edit_delivery', id=id)
        return redirect(_r)
    product_id = item.product_id
    is_despachador = getattr(current_user, 'role', None) == 'despachador'
    if is_despachador:
        pdps = ProductDeliveryPointStock.query.filter_by(product_id=product_id, delivery_point_id=delivery.delivery_point_id).first()
        available = (pdps.quantity if pdps else 0)
        stock_msg = 'en su almacén de entrega'
    else:
        pws = ProductWarehouseStock.query.filter_by(product_id=product_id, warehouse_id=delivery.warehouse_id).first()
        available = (pws.quantity if pws else 0)
        stock_msg = 'en bodega'
    # Total que quedaría en el despacho para este producto: otros ítems del mismo producto + nueva cantidad de este ítem
    other_qty = sum(i.quantity for i in delivery.items if i.product_id == product_id and i.id != item_id)
    total_wanted = other_qty + quantity
    if total_wanted > available:
        flash(f'Stock insuficiente {stock_msg}. Disponible: {available}, solicitado: {total_wanted}.', 'danger')
        _r = url_for('delivery.tablet_dispatch', id=id) if is_despachador else url_for('delivery.edit_delivery', id=id)
        return redirect(_r)
    item.quantity = quantity
    db.session.commit()
    flash('Cantidad actualizada.', 'success')
    if is_despachador:
        return redirect(url_for('delivery.tablet_dispatch', id=id))
    return redirect(url_for('delivery.edit_delivery', id=id))


@delivery_bp.route('/<int:id>/confirm', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal', 'despachador'])
def confirm_delivery(id):
    delivery = _get_delivery(id)
    if not _despachador_can_access(delivery):
        flash('No puede confirmar este despacho.', 'danger')
        return redirect(url_for('delivery.tablet_view'))
    if delivery.status != 'borrador':
        flash('Este despacho ya está confirmado o anulado.', 'warning')
        return redirect(url_for('delivery.view_delivery', id=id))
    if not delivery.items:
        flash('Agregue al menos un ítem antes de confirmar.', 'danger')
        return redirect(url_for('delivery.edit_delivery', id=id))
    form = DeliveryConfirmForm()
    if form.validate_on_submit():
        delivery.recipient_name = form.recipient_name.data or None
        delivery.recipient_document_number = form.recipient_document_number.data or None
        delivery.recipient_document_type = form.recipient_document_type.data or None
        delivery.delivered_at = datetime.utcnow()
        # Subir evidencias si se enviaron archivos
        upload_dir = os.path.join(_upload_folder(), str(delivery.id))
        os.makedirs(upload_dir, exist_ok=True)
        allowed = {'image/jpeg', 'image/png', 'image/gif', 'application/pdf'}
        for key in ('file', 'files'):
            files = request.files.getlist(key) or ([request.files.get(key)] if request.files.get(key) else [])
            for f in files:
                if not f or not f.filename:
                    continue
                if f.content_type and f.content_type not in allowed:
                    continue
                ext = os.path.splitext(secure_filename(f.filename))[1] or '.bin'
                filename = f"{uuid.uuid4().hex}{ext}"
                filepath = os.path.join(upload_dir, filename)
                f.save(filepath)
                rel_path = os.path.join(str(delivery.id), filename)
                db.session.add(DeliveryEvidence(delivery_id=delivery.id, file_path=rel_path, file_type=f.content_type or '', original_filename=secure_filename(f.filename)))
        is_despachador = getattr(current_user, 'role', None) == 'despachador'
        product_ids_affected = set()
        if is_despachador:
            # Entrega a particular: se descuenta solo del inventario del almacén de entrega del despachador
            for item in delivery.items:
                pdps = ProductDeliveryPointStock.query.filter_by(
                    product_id=item.product_id, delivery_point_id=delivery.delivery_point_id
                ).first()
                if not pdps or pdps.quantity < item.quantity:
                    flash(f'Stock insuficiente en su almacén de entrega para {item.product.name}. Solicite al centro de acopio si lo necesita.', 'danger')
                    return redirect(url_for('delivery.confirm_delivery', id=id))
                pdps.quantity -= item.quantity
                if pdps.quantity <= 0:
                    db.session.delete(pdps)
                product_ids_affected.add(item.product_id)
        else:
            # Bodega/admin: transferencia centro de acopio → punto (restar bodega, sumar al punto)
            for item in delivery.items:
                pws = ProductWarehouseStock.query.filter_by(
                    product_id=item.product_id, warehouse_id=delivery.warehouse_id
                ).first()
                if not pws or pws.quantity < item.quantity:
                    flash(f'Stock insuficiente en bodega para {item.product.name}.', 'danger')
                    return redirect(url_for('delivery.confirm_delivery', id=id))
                pws.quantity -= item.quantity
                pdps = ProductDeliveryPointStock.query.filter_by(
                    product_id=item.product_id, delivery_point_id=delivery.delivery_point_id
                ).first()
                if pdps:
                    pdps.quantity += item.quantity
                else:
                    db.session.add(ProductDeliveryPointStock(
                        product_id=item.product_id,
                        delivery_point_id=delivery.delivery_point_id,
                        quantity=item.quantity
                    ))
                product_ids_affected.add(item.product_id)
        for pid in product_ids_affected:
            product = Product.query.get(pid)
            if product and not is_despachador:
                new_total = sum(p.quantity for p in ProductWarehouseStock.query.filter_by(product_id=pid).all())
                prev_total = product.stock
                product.stock = new_total
                movement = InventoryMovement(
                    product_id=product.id,
                    movement_type='sale',
                    quantity=0,
                    previous_stock=prev_total,
                    new_stock=new_total,
                    reference_type='delivery',
                    reference_id=delivery.id,
                    user_id=current_user.id,
                    notes=f'Despacho {delivery.delivery_number}'
                )
                db.session.add(movement)
        delivery.status = 'confirmado'
        # Si el despacho proviene de un pedido, marcar el pedido como recibido
        linked_order = DispatchOrder.query.filter_by(delivery_id=delivery.id).first()
        if linked_order:
            linked_order.status = 'recibido'
        db.session.commit()
        log_audit('update', 'delivery', delivery.id, {'action': 'confirm', 'delivery_number': delivery.delivery_number})
        flash(f'Despacho {delivery.delivery_number} confirmado.', 'success')
        return redirect(url_for('delivery.view_delivery', id=id))
    return render_template('delivery/confirm.html', delivery=delivery, form=form, now=datetime.utcnow(), title='Confirmar Entrega')


@delivery_bp.route('/<int:id>/cancel', methods=['POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal', 'despachador'])
def cancel_delivery(id):
    delivery = _get_delivery(id)
    if not _despachador_can_access(delivery):
        flash('No puede anular este despacho.', 'danger')
        return redirect(url_for('delivery.tablet_view'))
    if delivery.status != 'borrador':
        flash('Solo se puede anular un despacho en borrador.', 'warning')
        return redirect(url_for('delivery.view_delivery', id=id))
    delivery.status = 'anulado'
    db.session.commit()
    flash('Despacho anulado.', 'success')
    return redirect(url_for('delivery.list_deliveries'))


def _upload_folder():
    root = current_app.config.get('UPLOAD_FOLDER') or os.path.join(current_app.instance_path, 'uploads')
    return os.path.join(root, 'deliveries')


@delivery_bp.route('/<int:id>/evidence', methods=['POST'])
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal', 'despachador'])
def upload_evidence(id):
    delivery = _get_delivery(id)
    if not _despachador_can_access(delivery):
        flash('No puede subir evidencias a este despacho.', 'danger')
        return redirect(url_for('delivery.tablet_view'))
    if 'file' not in request.files and 'files' not in request.files:
        flash('Ningún archivo seleccionado.', 'warning')
        return redirect(request.referrer or url_for('delivery.view_delivery', id=id))
    upload_dir = os.path.join(_upload_folder(), str(delivery.id))
    os.makedirs(upload_dir, exist_ok=True)
    allowed = {'image/jpeg', 'image/png', 'image/gif', 'application/pdf'}
    files = request.files.getlist('files') or request.files.getlist('file') or [request.files.get('file')]
    for f in files:
        if not f or not f.filename:
            continue
        if f.content_type and f.content_type not in allowed:
            flash(f'Tipo no permitido: {f.filename}. Use imagen o PDF.', 'danger')
            continue
        ext = os.path.splitext(secure_filename(f.filename))[1] or '.bin'
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(upload_dir, filename)
        f.save(filepath)
        rel_path = os.path.join(str(delivery.id), filename)
        ev = DeliveryEvidence(
            delivery_id=delivery.id,
            file_path=rel_path,
            file_type=f.content_type or '',
            original_filename=secure_filename(f.filename)
        )
        db.session.add(ev)
    db.session.commit()
    flash('Evidencia(s) subida(s).', 'success')
    return redirect(request.referrer or url_for('delivery.view_delivery', id=id))


@delivery_bp.route('/<int:id>/evidence/<path:filename>')
@login_required
@role_required(['admin', 'super_admin', 'bodega_principal', 'despachador'])
def serve_evidence(id, filename):
    delivery = _get_delivery(id)
    if not _despachador_can_access(delivery):
        from flask import abort
        abort(403)
    evs = DeliveryEvidence.query.filter_by(delivery_id=delivery.id).all()
    ev = next((e for e in evs if os.path.basename(e.file_path) == filename), None)
    if not ev:
        from flask import abort
        abort(404)
    folder = os.path.join(_upload_folder(), str(delivery.id))
    name = os.path.basename(ev.file_path)
    return send_from_directory(folder, name, as_attachment=False)
