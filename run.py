import os
from app import create_app

app = create_app()

FLASK_HOST = os.environ.get('FLASK_HOST', '0.0.0.0').strip()
FLASK_PORT = int(os.environ.get('FLASK_PORT', '5000'))


def _local_ip():
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


if __name__ == '__main__':
    try:
        debug_mode = (
            os.environ.get('FLASK_ENV') != 'production'
            and os.environ.get('FLASK_DEBUG', '1') != '0'
        )
        if os.environ.get('FLASK_ENV') == 'production':
            print('[ADVERTENCIA] Para producción use: python start.py --production o waitress-serve run:app')
        print(f"\n[Servidor] Escuchando en {FLASK_HOST}:{FLASK_PORT}")
        print(f"  Este equipo:  http://127.0.0.1:{FLASK_PORT}")
        lan_ip = _local_ip()
        if FLASK_HOST == '0.0.0.0' and lan_ip:
            print(f"  Red local:    http://{lan_ip}:{FLASK_PORT}")
        print()
        app.run(host=FLASK_HOST, port=FLASK_PORT, debug=debug_mode, use_reloader=False)
    except Exception as e:
        print(f"Error al iniciar el servidor: {e}")
        import traceback
        traceback.print_exc()
