"""Helper functions for multi-tenant architecture"""
from flask import current_app
from flask_login import current_user
from functools import wraps
from flask import abort


def get_company_default_tax_rate(company_id):
    """Tasa de IVA por defecto. Devuelve 0 (no calcular ni sumar IVA en cotizaciones ni facturas)."""
    # Plataforma sin IVA: siempre 0%. Para volver a usar IVA por empresa, descomentar y usar config:
    # from app.models import CompanyConfig
    # if company_id:
    #     config = CompanyConfig.query.filter_by(company_id=company_id).first()
    #     if config and config.default_tax_rate is not None:
    #         return float(config.default_tax_rate)
    return 0.0

def get_current_company_id():
    """Obtiene el company_id del usuario actual"""
    if current_user.is_authenticated:
        return current_user.company_id
    return None

def is_super_admin():
    """Verifica si el usuario actual es super_admin"""
    if current_user.is_authenticated:
        return current_user.role == 'super_admin'
    return False

def filter_by_company(query, model_class):
    """Filtra una consulta por el company_id del usuario actual.
    Los super-admins no ven datos de empresas (solo administran empresas y usuarios)."""
    if is_super_admin():
        return query.filter(False)  # Super-admin no ve datos de negocio
    company_id = get_current_company_id()
    if company_id:
        return query.filter(model_class.company_id == company_id)
    return query.filter(False)  # No devolver nada si no hay company_id

def ensure_company_access(entity):
    """Valida que una entidad pertenezca a la empresa del usuario actual"""
    if not entity:
        abort(404)
    
    company_id = get_current_company_id()
    if not company_id:
        abort(403)
    
    # Verificar que la entidad tenga company_id y que coincida
    if hasattr(entity, 'company_id') and entity.company_id != company_id:
        abort(403)
    
    return entity

def ensure_company_id(entity_id, model_class):
    """Valida que un ID pertenezca a la empresa del usuario actual.
    Los super-admins solo pueden acceder a la entidad Company (para administrarla)."""
    # Super-admins solo administran empresas y usuarios; no acceden a datos de negocio
    if is_super_admin():
        if model_class.__name__ in ('Company', 'User'):
            return model_class.query.get_or_404(entity_id)
        abort(403)  # No puede abrir facturas, clientes, productos, etc.

    company_id = get_current_company_id()
    if not company_id:
        abort(403)
    
    # Caso especial: Company no tiene company_id, es la entidad raíz
    if model_class.__name__ == 'Company':
        entity = model_class.query.get_or_404(entity_id)
        # Verificar que el usuario solo pueda acceder a su propia empresa
        if entity.id != company_id:
            abort(403)
        return entity
    
    # Para otras entidades, usar company_id
    entity = model_class.query.filter_by(id=entity_id, company_id=company_id).first_or_404()
    return entity

def ensure_company_access_decorator(f):
    """Decorador para asegurar que el usuario solo acceda a datos de su empresa"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # El decorador se aplicará en las rutas específicas
        # La validación se hará usando ensure_company_id o ensure_company_access
        return f(*args, **kwargs)
    return decorated_function
