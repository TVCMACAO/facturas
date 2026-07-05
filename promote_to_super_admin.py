#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Asigna el rol super_admin (Administrador general) a un usuario existente por nombre de usuario.
Uso: python promote_to_super_admin.py <username>
Ejemplo: python promote_to_super_admin.py hemmis
"""
import sys
from app import create_app, db
from app.models import User

def promote(username):
    app = create_app()
    with app.app_context():
        # Usuario puede existir en más de una empresa (username único por company_id)
        users = User.query.filter_by(username=username).all()
        if not users:
            print(f"[ERROR] No existe ningún usuario con nombre de usuario '{username}'.")
            return 1
        if len(users) > 1:
            print(f"[INFO] Hay {len(users)} usuarios con username '{username}' (distintas empresas). Se actualizará el primero.")
        u = users[0]
        if u.role == 'super_admin':
            print(f"[INFO] El usuario '{username}' ya tiene rol super_admin (Administrador general).")
            return 0
        u.role = 'super_admin'
        db.session.commit()
        print(f"[OK] Usuario '{username}' (id={u.id}) actualizado a rol super_admin (Administrador general).")
        return 0

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python promote_to_super_admin.py <username>")
        print("Ejemplo: python promote_to_super_admin.py hemmis")
        sys.exit(1)
    username = sys.argv[1].strip()
    sys.exit(promote(username))
