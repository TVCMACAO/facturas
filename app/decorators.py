from functools import wraps
from flask import flash, redirect, url_for, abort, request
from flask_login import current_user
from app import db
from app.models import AuditLog
import json
import datetime

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Por favor, inicia sesión para acceder a esta página.', 'warning')
                return redirect(url_for('main.login'))
            if current_user.role not in allowed_roles:
                flash('No tienes permiso para acceder a esta página.', 'danger')
                abort(403) # Forbidden
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_audit(action, entity_type, entity_id, changes=None, user=None):
    """
    Registra una acción en el log de auditoría.
    
    Args:
        action: Acción realizada ('create', 'update', 'delete', 'view')
        entity_type: Tipo de entidad ('invoice', 'quote', 'product', etc.)
        entity_id: ID de la entidad
        changes: Diccionario con cambios (opcional)
        user: Usuario que realiza la acción (opcional, usa current_user si no se proporciona)
    """
    if not user:
        user = current_user if current_user.is_authenticated else None
    
    if not user:
        return  # No registrar si no hay usuario
    
    try:
        changes_json = json.dumps(changes) if changes else None
        ip_address = request.remote_addr if request else None
        user_agent = request.headers.get('User-Agent') if request else None
        
        audit_entry = AuditLog(
            user_id=user.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=changes_json,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.datetime.utcnow()
        )
        db.session.add(audit_entry)
        db.session.commit()
    except Exception as e:
        # No fallar si hay error en auditoría
        db.session.rollback()
        pass
