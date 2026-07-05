#!/usr/bin/env python
"""Ejecuta la migración: UPDATE user SET role = 'despachador' WHERE role = 'minorista'."""
import os
import sys

basedir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, basedir)

from dotenv import load_dotenv
load_dotenv(os.path.join(basedir, '.env'))

from app import create_app, db
from app.models import User

def main():
    app = create_app()
    with app.app_context():
        count = User.query.filter_by(role='minorista').update({'role': 'despachador'})
        db.session.commit()
        print(f'Migración aplicada: {count} usuario(s) actualizado(s) de rol minorista a despachador.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
