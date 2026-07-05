import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'), verbose=True)

DEFAULT_SECRET_KEY = 'una-clave-secreta-muy-dificil-de-adivinar'


def clean_env_var(value):
    """
    Limpia comillas simples y dobles de las variables de entorno.
    Útil cuando las variables se definen con comillas en el archivo .env
    """
    if value is None:
        return None
    value = str(value).strip()
    if (value.startswith('"') and value.endswith('"')) or \
       (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]
    return value


def is_production_env():
    return clean_env_var(os.environ.get('FLASK_ENV')) == 'production'


class Config:
    SECRET_KEY = clean_env_var(os.environ.get('SECRET_KEY')) or DEFAULT_SECRET_KEY

    _database_url = clean_env_var(os.environ.get('DATABASE_URL'))
    SQLALCHEMY_DATABASE_URI = _database_url or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    WTF_CSRF_ENABLED = True

    MAIL_SERVER = clean_env_var(os.environ.get('MAIL_SERVER')) or 'smtp.googlemail.com'
    MAIL_PORT = int(clean_env_var(os.environ.get('MAIL_PORT')) or 587)
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = clean_env_var(os.environ.get('MAIL_USERNAME'))
    MAIL_PASSWORD = clean_env_var(os.environ.get('MAIL_PASSWORD'))
    MAIL_DEFAULT_SENDER = clean_env_var(os.environ.get('MAIL_DEFAULT_SENDER')) or 'no-reply@yourdomain.com'

    WHATSAPP_ACCESS_TOKEN = clean_env_var(os.environ.get('WHATSAPP_ACCESS_TOKEN'))
    WHATSAPP_PHONE_NUMBER_ID = clean_env_var(os.environ.get('WHATSAPP_PHONE_NUMBER_ID'))
    WHATSAPP_BUSINESS_ACCOUNT_ID = clean_env_var(os.environ.get('WHATSAPP_BUSINESS_ACCOUNT_ID'))

    DEFAULT_TAX_RATE = float(clean_env_var(os.environ.get('DEFAULT_TAX_RATE')) or 19.0)
    MONTHLY_SALES_TARGET = float(clean_env_var(os.environ.get('MONTHLY_SALES_TARGET')) or 10000.0)
    TESSERACT_CMD = clean_env_var(os.environ.get('TESSERACT_CMD')) or ''

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    @staticmethod
    def validate_config():
        errors = []
        production = is_production_env()

        if production:
            if not Config.SECRET_KEY or Config.SECRET_KEY == DEFAULT_SECRET_KEY:
                errors.append(
                    "ERROR: En producción debe definir SECRET_KEY única en variables de entorno."
                )
        elif not Config.SECRET_KEY or Config.SECRET_KEY == DEFAULT_SECRET_KEY:
            errors.append(
                "ADVERTENCIA: SECRET_KEY no está configurada. Usando valor por defecto (solo desarrollo)."
            )

        db_uri = Config.SQLALCHEMY_DATABASE_URI
        if not db_uri:
            errors.append("ERROR: SQLALCHEMY_DATABASE_URI no está configurada.")
        elif db_uri.startswith('sqlite'):
            db_path = db_uri.replace('sqlite:///', '')
            db_dir = os.path.dirname(db_path) if os.path.dirname(db_path) else '.'
            if db_dir and not os.path.exists(db_dir):
                errors.append(
                    f"ADVERTENCIA: El directorio para la base de datos SQLite no existe: {db_dir}"
                )
        elif production and db_uri.startswith('mysql://') and 'mysqlconnector' not in db_uri:
            errors.append(
                "ERROR: DATABASE_URL debe usar mysql+mysqlconnector:// (no mysql://). "
                "Ejemplo: mysql+mysqlconnector://user:pass@host:3306/ventas"
            )

        is_valid = not any(e.startswith('ERROR:') for e in errors)
        return is_valid, errors


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True

    @staticmethod
    def validate_config():
        is_valid, errors = Config.validate_config()
        if not Config.SECRET_KEY or Config.SECRET_KEY == DEFAULT_SECRET_KEY:
            msg = "ERROR: SECRET_KEY obligatoria en producción."
            if msg not in errors:
                errors.append(msg)
        return False if any(e.startswith('ERROR:') for e in errors) else is_valid, errors


def get_config():
    if is_production_env():
        return ProductionConfig
    return Config
