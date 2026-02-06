
from app import create_app
from waitress import serve
import os

# Desactiva el modo de depuración para producción
os.environ['FLASK_DEBUG'] = '0'

app = create_app()

if __name__ == '__main__':
    print("Iniciando servidor de producción en http://0.0.0.0:8080")
    serve(app, host='0.0.0.0', port=8080)
