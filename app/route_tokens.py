"""
Router de URLs con token: todas las rutas autenticadas exigen un token en la URL.
Generación centralizada y validación en cada petición.
"""
import time
from flask import current_app, request
from flask_login import current_user

PATH_PREFIXES_WITHOUT_TOKEN = (
    '/',
    '/index',
    '/login',
    '/register',
    '/logout',
    '/request_password_reset',
    '/reset_password',
    '/select_company',
    '/static',
    '/favicon.ico',
    '/health',
    '/.well-known',
)

def path_requires_token(path):
    if not path or path == '/':
        return False
    path = path.rstrip('/') or '/'
    for prefix in PATH_PREFIXES_WITHOUT_TOKEN:
        if path == prefix or path.startswith(prefix + '/') or path.startswith(prefix + '?'):
            return False
    return True


_PATH_ACTION_SEGMENTS = frozenset({'send_email', 'pdf', 'convert_to_invoice', 'send_whatsapp'})


def get_token_from_path(path):
    if not path:
        return None
    parts = path.split('/')
    if len(parts) >= 4 and parts[1] == 'quotes':
        candidate = parts[3]
        if len(parts) == 5:
            return candidate
        if len(parts) == 4 and candidate not in _PATH_ACTION_SEGMENTS:
            return candidate
    if len(parts) >= 4 and parts[1] == 'invoices':
        candidate = parts[3]
        if len(parts) == 5:
            return candidate
        if len(parts) == 4 and candidate not in _PATH_ACTION_SEGMENTS:
            return candidate
    return None


def generate_route_token(path, max_age_seconds=3600):
    from itsdangerous import URLSafeTimedSerializer
    path_part = path.split('?')[0].rstrip('/') or '/'
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    payload = {
        'user_id': current_user.id,
        'path': path_part,
        'exp': int(time.time()) + max_age_seconds,
    }
    return serializer.dumps(payload, salt='route-token')


def validate_view_token_entity(token, entity_id, entity_type, max_age_seconds=3600):
    if not token or not current_user.is_authenticated:
        return False
    from itsdangerous import URLSafeTimedSerializer
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        data = serializer.loads(token, salt='view-token', max_age=max_age_seconds)
        expected = f"{entity_type}:{entity_id}"
        return data == expected
    except Exception:
        return False


def validate_route_token(token, path, max_age_seconds=3600):
    if not token or not current_user.is_authenticated:
        return False
    path_part = path.split('?')[0].rstrip('/') or '/'
    from itsdangerous import URLSafeTimedSerializer, BadSignature
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        payload = serializer.loads(token, salt='route-token', max_age=max_age_seconds)
        return payload.get('user_id') == current_user.id and payload.get('path') == path_part
    except (BadSignature, Exception):
        return False


def url_with_token(endpoint, **values):
    from flask import url_for
    base = url_for(endpoint, **values)
    if not current_user.is_authenticated:
        return base
    path_for_token = base.split('?')[0]
    token = generate_route_token(path_for_token)
    sep = '&' if '?' in base else '?'
    return f"{base}{sep}token={token}"
