"""Tokens para rutas de administración que exigen token en la URL."""
import time
from flask import current_app
from flask_login import current_user


def generate_admin_route_token(route_name, max_age_seconds=3600):
    """Genera un token firmado para acceder a una ruta de admin. Válido max_age_seconds (default 1 hora)."""
    from itsdangerous import URLSafeTimedSerializer
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    payload = {
        'user_id': current_user.id,
        'route': route_name,
        'exp': int(time.time()) + max_age_seconds,
    }
    return serializer.dumps(payload, salt='admin-route')


def validate_admin_route_token(token, route_name, max_age_seconds=3600):
    """Valida el token para la ruta indicada. Devuelve True si es válido."""
    if not token or not current_user.is_authenticated:
        return False
    from itsdangerous import URLSafeTimedSerializer, BadSignature
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        payload = serializer.loads(token, salt='admin-route', max_age=max_age_seconds)
        return payload.get('user_id') == current_user.id and payload.get('route') == route_name
    except (BadSignature, Exception):
        return False
