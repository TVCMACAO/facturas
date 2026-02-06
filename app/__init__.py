from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail # Import Mail
from flask_babel import Babel # Import Babel
from babel.numbers import format_decimal # Import format_decimal

db = SQLAlchemy()
login = LoginManager()
login.login_view = 'main.login'
mail = Mail() # Initialize Mail
babel = Babel() # Initialize Babel

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login.init_app(app)
    mail.init_app(app) # Initialize Mail with app
    babel.init_app(app) # Initialize Babel with app
    app.config['BABEL_DEFAULT_LOCALE'] = 'es' # Set default locale directly

    # Register custom Jinja2 filter for currency formatting
    @app.template_filter('currency_format')
    def currency_format_filter(value, currency_symbol='$', locale='es'):
        if value is None:
            return ""
        # Format with thousands separator and 2 decimal places
        formatted_value = format_decimal(value, format='#,##0.00', locale=locale)
        return f"{currency_symbol}{formatted_value}"

    # Register Flask-Babel's format_date as a custom filter
    @app.template_filter('format_date')
    def _format_date_filter(date, format='medium'):
        from flask_babel import format_date as _babel_format_date
        return _babel_format_date(date, format=format)
    
    # Register filter for generating view tokens
    @app.template_filter('view_token')
    def view_token_filter(entity_id, entity_type='quote'):
        """Genera un token temporal para acceder a una vista
        Uso: {{ quote.id|view_token('quote') }}
        """
        from itsdangerous import URLSafeTimedSerializer
        serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
        data = f"{entity_type}:{entity_id}"
        return serializer.dumps(data, salt='view-token')

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

    from app.routes.credit_note import credit_notes_bp
    app.register_blueprint(credit_notes_bp)

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import render_template, redirect, url_for
        from flask_login import current_user
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

    with app.app_context():
        db.create_all()

    return app