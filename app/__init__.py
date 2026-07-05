from flask import Flask
from config import get_config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_babel import Babel
from flask_wtf.csrf import CSRFProtect
from babel.numbers import format_decimal

db = SQLAlchemy()
login = LoginManager()
login.login_view = 'main.login'
mail = Mail()
babel = Babel()
csrf = CSRFProtect()

def create_app(config_class=None):
    if config_class is None:
        config_class = get_config()

    is_valid, config_errors = config_class.validate_config()
    if not is_valid:
        raise RuntimeError(
            "Configuración inválida:\n" + "\n".join(config_errors)
        )

    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login.init_app(app)
    mail.init_app(app)
    babel.init_app(app)
    csrf.init_app(app)
    app.config['BABEL_DEFAULT_LOCALE'] = 'es'

    @app.template_filter('currency_format')
    def currency_format_filter(value, currency_symbol='$', locale='es'):
        if value is None:
            return ""
        formatted_value = format_decimal(value, format='#,##0.00', locale=locale)
        return f"{currency_symbol}{formatted_value}"

    @app.template_filter('format_date')
    def _format_date_filter(date, format='medium'):
        from flask_babel import format_date as _babel_format_date
        return _babel_format_date(date, format=format)

    ROLE_LABELS = {
        'admin': 'Administrador de empresa',
        'bodega_principal': 'Bodega principal',
        'minorista': 'Despachador',
        'user': 'Usuario de ventas',
        'despachador': 'Despachador',
        'super_admin': 'Administrador general',
    }
    @app.template_filter('role_label')
    def role_label_filter(role_value):
        return ROLE_LABELS.get(role_value, role_value or 'Usuario')

    WAREHOUSE_TYPE_LABELS = {
        'general': 'Almacén General',
        'farmacia': 'Farmacia',
        'mayorista': 'Almacén General',
        'minorista': 'Farmacia',
    }
    @app.template_filter('warehouse_type_label')
    def warehouse_type_label_filter(warehouse_type):
        return WAREHOUSE_TYPE_LABELS.get(warehouse_type, warehouse_type or '—')

    @app.template_filter('view_token')
    def view_token_filter(entity_id, entity_type='quote'):
        from itsdangerous import URLSafeTimedSerializer
        serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
        data = f"{entity_type}:{entity_id}"
        return serializer.dumps(data, salt='view-token')

    @app.route('/health')
    @app.route('/api/health')
    def health():
        from app.version import APP_BUILD_ID
        return {'status': 'ok', 'build': APP_BUILD_ID}, 200

    with app.app_context():
        from app.startup_tasks import backfill_null_company_ids
        backfill_null_company_ids(app)
        app.logger.info('App build=%s', __import__('app.version', fromlist=['APP_BUILD_ID']).APP_BUILD_ID)

    from app.routes.main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from app.routes.client import clients_bp
    app.register_blueprint(clients_bp)

    from app.routes.product import products_bp
    app.register_blueprint(products_bp)

    from app.routes.quote import quotes_bp
    app.register_blueprint(quotes_bp)

    from app.routes.invoice import invoices_bp
    app.register_blueprint(invoices_bp)

    from app.routes.inventory import inventory_bp
    app.register_blueprint(inventory_bp)

    from app.routes.admin import admin_bp
    app.register_blueprint(admin_bp)
    from app.routes.transfer import transfer_bp
    app.register_blueprint(transfer_bp)
    from app.routes.delivery import delivery_bp
    app.register_blueprint(delivery_bp)
    from app.routes.dispatch_order import dispatch_order_bp
    app.register_blueprint(dispatch_order_bp)
    from app.routes.reception import reception_bp
    app.register_blueprint(reception_bp)

    from app.routes.credit_note import credit_notes_bp
    app.register_blueprint(credit_notes_bp)

    @app.context_processor
    def inject_csrf():
        from flask_wtf.csrf import generate_csrf
        return {'csrf_token': generate_csrf()}

    @app.context_processor
    def inject_company():
        from flask_login import current_user
        if current_user.is_authenticated and hasattr(current_user, 'company'):
            return {'current_company': current_user.company}
        return {'current_company': None}

    @app.context_processor
    def inject_pending_dispatch_orders():
        from flask_login import current_user
        if current_user.is_authenticated and getattr(current_user, 'role', None) in ('admin', 'bodega_principal') and current_user.company_id:
            from app.models import DispatchOrder
            count = DispatchOrder.query.filter_by(company_id=current_user.company_id).filter(
                DispatchOrder.status.in_(['pendiente', 'en_preparacion'])
            ).count()
            return {'pending_dispatch_orders_count': count}
        return {'pending_dispatch_orders_count': 0}

    @app.context_processor
    def inject_url_with_token():
        from app.route_tokens import url_with_token as _url_with_token
        return {'url_with_token': _url_with_token}

    @app.before_request
    def require_route_token():
        from flask import redirect, url_for, request
        from flask_login import current_user
        from app.route_tokens import (
            path_requires_token, validate_route_token, generate_route_token,
            get_token_from_path, validate_view_token_entity,
        )
        from urllib.parse import urlencode, parse_qs
        if not current_user.is_authenticated:
            return None
        path = request.path
        if not path_requires_token(path):
            return None
        token = request.args.get('token') or get_token_from_path(path)
        if token:
            parts = path.strip('/').split('/')
            if len(parts) >= 3 and parts[0] == 'quotes':
                try:
                    entity_id = int(parts[1])
                    if validate_view_token_entity(token, entity_id, 'quote'):
                        return None
                except ValueError:
                    pass
            if len(parts) >= 3 and parts[0] == 'invoices':
                try:
                    entity_id = int(parts[1])
                    if validate_view_token_entity(token, entity_id, 'invoice'):
                        return None
                except ValueError:
                    pass
        if validate_route_token(token, path):
            return None
        if not token:
            new_token = generate_route_token(path)
            qs = parse_qs(request.query_string.decode() if isinstance(request.query_string, bytes) else request.query_string)
            qs['token'] = [new_token]
            new_url = path + ('?' + urlencode(qs, doseq=True))
            return redirect(new_url)
        from flask import flash
        flash('Enlace no válido o expirado. Use el menú para navegar.', 'warning')
        return redirect(url_for('main.index'))

    @app.errorhandler(404)
    def not_found_error(error):
        from flask import render_template, redirect, url_for, request, jsonify
        from flask_login import current_user
        if request.path in ('/health', '/api/health'):
            from app.version import APP_BUILD_ID
            return jsonify({'status': 'ok', 'build': APP_BUILD_ID}), 200
        if not current_user.is_authenticated:
            return redirect(url_for('main.login'))
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden_error(error):
        from flask import render_template, redirect, url_for
        from flask_login import current_user
        if not current_user.is_authenticated:
            return redirect(url_for('main.login'))
        return render_template('errors/403.html'), 403

    return app
