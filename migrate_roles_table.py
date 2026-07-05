#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Migración: crear tabla roles, pasar user.role a user.role_id.
Puede ejecutar manualmente el SQL (migrate_roles_table.sql) o este script:
  python migrate_roles_table.py
Ejecutar UNA sola vez. La BD debe tener aún la columna user.role al ejecutar.
"""
import sys
from sqlalchemy import text
from app import create_app, db

ROLES_DATA = [
    ('super_admin', 'Administrador general'),
    ('admin', 'Administrador de empresa'),
    ('user', 'Usuario de ventas'),
    ('bodega_principal', 'Bodega principal'),
    ('despachador', 'Despachador'),
    ('minorista', 'Despachador'),  # legacy, por si existe en BD
]

def run_migration():
    app = create_app()
    with app.app_context():
        engine = db.engine
        with engine.connect() as conn:
            # 1. Crear tabla roles si no existe
            if engine.dialect.name == 'mysql':
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS roles (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        code VARCHAR(64) NOT NULL UNIQUE,
                        label VARCHAR(128) NOT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS roles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        code VARCHAR(64) NOT NULL UNIQUE,
                        label VARCHAR(128) NOT NULL
                    )
                """))
            conn.commit()

            # 2. Insertar roles (ignorar si ya existen)
            for code, label in ROLES_DATA:
                try:
                    if engine.dialect.name == 'mysql':
                        conn.execute(text(
                            "INSERT IGNORE INTO roles (code, label) VALUES (:code, :label)"
                        ), {"code": code, "label": label})
                    else:
                        conn.execute(text(
                            "INSERT OR IGNORE INTO roles (code, label) VALUES (:code, :label)"
                        ), {"code": code, "label": label})
                except Exception:
                    pass
            conn.commit()

            # 3. Añadir columna role_id si no existe
            try:
                if engine.dialect.name == 'mysql':
                    conn.execute(text("ALTER TABLE user ADD COLUMN role_id INT NULL"))
                else:
                    conn.execute(text("ALTER TABLE user ADD COLUMN role_id INTEGER NULL"))
                conn.commit()
            except Exception as e:
                if 'Duplicate column' not in str(e) and 'duplicate column name' not in str(e).lower():
                    raise
                conn.rollback()

            # 4. Rellenar role_id desde user.role
            conn.execute(text("""
                UPDATE user u
                SET u.role_id = (SELECT id FROM roles r WHERE r.code = u.role LIMIT 1)
                WHERE u.role IS NOT NULL
            """))
            conn.commit()

            # 5. Asignar rol por defecto 'user' a los que quedaron sin role_id
            conn.execute(text("""
                UPDATE user SET role_id = (SELECT id FROM roles WHERE code = 'user' LIMIT 1)
                WHERE role_id IS NULL
            """))
            conn.commit()

            # 6. Hacer role_id NOT NULL
            if engine.dialect.name == 'mysql':
                conn.execute(text("ALTER TABLE user MODIFY COLUMN role_id INT NOT NULL"))
            else:
                conn.execute(text("ALTER TABLE user MODIFY COLUMN role_id INTEGER NOT NULL"))
            conn.commit()

            # 7. Eliminar columna role (MySQL: quitar FK si hubiera; aquí no hay)
            if engine.dialect.name == 'mysql':
                conn.execute(text("ALTER TABLE user DROP COLUMN role"))
            else:
                conn.execute(text("ALTER TABLE user DROP COLUMN role"))
            conn.commit()

            # 8. Añadir FK role_id -> roles(id)
            try:
                if engine.dialect.name == 'mysql':
                    conn.execute(text(
                        "ALTER TABLE user ADD CONSTRAINT fk_user_role "
                        "FOREIGN KEY (role_id) REFERENCES roles(id)"
                    ))
                else:
                    conn.execute(text(
                        "CREATE INDEX IF NOT EXISTS ix_user_role_id ON user(role_id)"
                    ))
                conn.commit()
            except Exception as e:
                if 'Duplicate' not in str(e) and 'already exists' not in str(e).lower():
                    raise
                conn.rollback()

    print("[OK] Migración roles completada: tabla roles creada, user.role_id rellenado, user.role eliminada.")

if __name__ == '__main__':
    try:
        run_migration()
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
