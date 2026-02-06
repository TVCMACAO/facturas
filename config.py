import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'), verbose=True)


def clean_env_var(value):
    """
    Limpia comillas simples y dobles de las variables de entorno.
    Útil cuando las variables se definen con comillas en el archivo .env
    """
    if value is None:
        return None
    value = str(value).strip()
    # Remover comillas al inicio y final si existen
    if (value.startswith('"') and value.endswith('"')) or \
       (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]
    return value


class Config:
    SECRET_KEY = clean_env_var(os.environ.get('SECRET_KEY')) or 'una-clave-secreta-muy-dificil-de-adivinar'
    
    # Database Configuration - limpia comillas de DATABASE_URL
    _database_url = clean_env_var(os.environ.get('DATABASE_URL'))
    SQLALCHEMY_DATABASE_URI = _database_url or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Email Configuration
    MAIL_SERVER = clean_env_var(os.environ.get('MAIL_SERVER')) or 'smtp.googlemail.com'
    MAIL_PORT = int(clean_env_var(os.environ.get('MAIL_PORT')) or 587)
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = clean_env_var(os.environ.get('MAIL_USERNAME'))
    MAIL_PASSWORD = clean_env_var(os.environ.get('MAIL_PASSWORD'))
    MAIL_DEFAULT_SENDER = clean_env_var(os.environ.get('MAIL_DEFAULT_SENDER')) or 'no-reply@yourdomain.com'

    # WhatsApp Configuration
    WHATSAPP_ACCESS_TOKEN = clean_env_var(os.environ.get('WHATSAPP_ACCESS_TOKEN'))
    WHATSAPP_PHONE_NUMBER_ID = clean_env_var(os.environ.get('WHATSAPP_PHONE_NUMBER_ID'))
    WHATSAPP_BUSINESS_ACCOUNT_ID = clean_env_var(os.environ.get('WHATSAPP_BUSINESS_ACCOUNT_ID'))
    
    # Tax Configuration
    DEFAULT_TAX_RATE = float(clean_env_var(os.environ.get('DEFAULT_TAX_RATE')) or 19.0)  # IVA por defecto 19%
    
    # Dashboard Configuration
    MONTHLY_SALES_TARGET = float(clean_env_var(os.environ.get('MONTHLY_SALES_TARGET')) or 10000.0)  # Meta mensual de ventas
    
    @staticmethod
    def validate_config():
        """
        Valida que la configuración mínima esté presente.
        Retorna (is_valid, errors) donde errors es una lista de mensajes de error.
        """
        errors = []
        
        # Validar SECRET_KEY
        if not Config.SECRET_KEY or Config.SECRET_KEY == 'una-clave-secreta-muy-dificil-de-adivinar':
            errors.append("ADVERTENCIA: SECRET_KEY no está configurada. Usando valor por defecto (no seguro para producción).")
        
        # Validar DATABASE_URL
        if not Config.SQLALCHEMY_DATABASE_URI:
            errors.append("ERROR: SQLALCHEMY_DATABASE_URI no está configurada.")
        elif Config.SQLALCHEMY_DATABASE_URI.startswith('sqlite'):
            # Para SQLite, verificar que el directorio existe (el archivo se creará automáticamente)
            db_path = Config.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')
            db_dir = os.path.dirname(db_path) if os.path.dirname(db_path) else '.'
            if db_dir and not os.path.exists(db_dir):
                errors.append(f"ADVERTENCIA: El directorio para la base de datos SQLite no existe: {db_dir}")
        
        return len(errors) == 0, errors