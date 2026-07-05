
import os
os.environ.setdefault('FLASK_ENV', 'production')
os.environ['FLASK_DEBUG'] = '0'

from app import create_app
from waitress import serve

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8080'))
    print(f"Iniciando servidor de producción en http://0.0.0.0:{port}")
    serve(app, host='0.0.0.0', port=port)
