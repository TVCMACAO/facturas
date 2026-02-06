#!/usr/bin/env python
"""
Script único e inteligente para iniciar el servidor Flask.
Detecta automáticamente el entorno y valida la configuración antes de iniciar.

Uso:
    python start.py                    # Modo desarrollo (por defecto)
    python start.py --production       # Modo producción
    python start.py --port 5000       # Especificar puerto
    python start.py --host 0.0.0.0    # Especificar host
    python start.py --check            # Solo validar configuración sin iniciar
"""

import os
import sys
import argparse
from config import Config


def check_dependencies():
    """Verifica que las dependencias principales estén instaladas."""
    missing = []
    
    try:
        import flask
    except ImportError:
        missing.append("flask")
    
    try:
        import flask_sqlalchemy
    except ImportError:
        missing.append("flask-sqlalchemy")
    
    try:
        import flask_login
    except ImportError:
        missing.append("flask-login")
    
    if missing:
        print("[ERROR] Faltan las siguientes dependencias:")
        for dep in missing:
            print(f"   - {dep}")
        print("\nInstala las dependencias con: pip install -r requirements.txt")
        return False
    
    return True


def validate_database_connection():
    """Intenta validar la conexión a la base de datos."""
    try:
        from app import create_app, db
        
        app = create_app()
        with app.app_context():
            # Intentar una consulta simple para verificar la conexión
            db.engine.connect()
            print("[OK] Conexion a la base de datos: OK")
            return True
    except Exception as e:
        print(f"[ADVERTENCIA] No se pudo validar la conexion a la base de datos: {e}")
        print("   El servidor se iniciara de todas formas, pero puede fallar al acceder a la base de datos.")
        return False


def print_config_info():
    """Muestra información sobre la configuración actual."""
    print("\n" + "="*60)
    print("CONFIGURACIÓN DEL SERVIDOR")
    print("="*60)
    
    # Información de base de datos
    db_uri = Config.SQLALCHEMY_DATABASE_URI
    if db_uri.startswith('sqlite'):
        print(f"[DB] Base de datos: SQLite ({db_uri.replace('sqlite:///', '')})")
    elif 'mysql' in db_uri:
        # Ocultar credenciales en la URL
        safe_uri = db_uri.split('@')[-1] if '@' in db_uri else db_uri
        print(f"[DB] Base de datos: MySQL ({safe_uri})")
    else:
        print(f"[DB] Base de datos: {db_uri[:50]}...")
    
    # Información de email
    if Config.MAIL_USERNAME:
        print(f"[EMAIL] Email configurado: {Config.MAIL_USERNAME}")
    else:
        print("[EMAIL] Email: No configurado")
    
    # Información de WhatsApp
    if Config.WHATSAPP_ACCESS_TOKEN:
        print("[WHATSAPP] WhatsApp: Configurado")
    else:
        print("[WHATSAPP] WhatsApp: No configurado")
    
    print("="*60 + "\n")


def run_development_server(host='127.0.0.1', port=5000):
    """Inicia el servidor en modo desarrollo."""
    from app import create_app
    
    app = create_app()
    
    print(f"\n[INICIANDO] Servidor en modo DESARROLLO")
    print(f"[URL] http://{host}:{port}")
    print(f"[DEBUG] Debug mode: ON")
    print(f"[INFO] Presiona Ctrl+C para detener el servidor\n")
    
    try:
        app.run(host=host, port=port, debug=True, use_reloader=False, threaded=True)
    except KeyboardInterrupt:
        print("\n\n⏹️  Servidor detenido por el usuario")
    except Exception as e:
        print(f"\n❌ ERROR al iniciar el servidor: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_production_server(host='0.0.0.0', port=8080):
    """Inicia el servidor en modo producción usando Waitress."""
    try:
        from waitress import serve
    except ImportError:
        print("[ERROR] waitress no esta instalado.")
        print("   Instalalo con: pip install waitress")
        sys.exit(1)
    
    from app import create_app
    
    app = create_app()
    
    # Desactivar modo debug para producción
    os.environ['FLASK_DEBUG'] = '0'
    app.config['DEBUG'] = False
    
    print(f"\n[INICIANDO] Servidor en modo PRODUCCION")
    print(f"[URL] http://{host}:{port}")
    print(f"[DEBUG] Debug mode: OFF")
    print(f"[INFO] Presiona Ctrl+C para detener el servidor\n")
    
    try:
        serve(app, host=host, port=port)
    except KeyboardInterrupt:
        print("\n\n⏹️  Servidor detenido por el usuario")
    except Exception as e:
        print(f"\n❌ ERROR al iniciar el servidor: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description='Inicia el servidor Flask de gestión de cotizaciones y facturas',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--production',
        action='store_true',
        help='Inicia el servidor en modo producción (usa Waitress)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=None,
        help='Puerto donde escuchará el servidor (por defecto: 5000 desarrollo, 8080 producción)'
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default=None,
        help='Host donde escuchará el servidor (por defecto: 127.0.0.1 desarrollo, 0.0.0.0 producción)'
    )
    
    parser.add_argument(
        '--check',
        action='store_true',
        help='Solo valida la configuración sin iniciar el servidor'
    )
    
    args = parser.parse_args()
    
    # Verificar dependencias
    print("[VERIFICANDO] Dependencias...")
    if not check_dependencies():
        sys.exit(1)
    print("[OK] Dependencias: OK")
    
    # Validar configuración
    print("\n[VALIDANDO] Configuracion...")
    is_valid, errors = Config.validate_config()
    if errors:
        for error in errors:
            print(f"[ADVERTENCIA] {error}")
    
    # Mostrar información de configuración
    print_config_info()
    
    # Si solo se solicita validación, salir aquí
    if args.check:
        print("[OK] Validacion completada")
        if not is_valid:
            print("[ADVERTENCIA] Se encontraron advertencias en la configuracion")
        sys.exit(0 if is_valid else 1)
    
    # Validar conexión a base de datos
    print("[VALIDANDO] Conexion a la base de datos...")
    validate_database_connection()
    
    # Determinar configuración de host y puerto
    if args.production:
        host = args.host or '0.0.0.0'
        port = args.port or 8080
        run_production_server(host, port)
    else:
        host = args.host or '127.0.0.1'
        port = args.port or 5000
        run_development_server(host, port)


if __name__ == '__main__':
    main()
