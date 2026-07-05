"""
Script para agregar la columna assigned_delivery_point_id a la tabla user.
Ejecutar cuando aparezca: Unknown column 'user.assigned_delivery_point_id' in 'field list'

  python add_despachador_column.py
"""
import sys
from sqlalchemy import text

def main():
    # Crear app solo para obtener la conexión a la BD (misma config que la aplicación)
    from app import create_app, db
    app = create_app()
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE `user` ADD COLUMN `assigned_delivery_point_id` INT NULL"))
                conn.commit()
            print("[OK] Columna 'assigned_delivery_point_id' agregada a la tabla 'user'.")
        except Exception as e:
            if "Duplicate column" in str(e) or "already exists" in str(e):
                print("[OK] La columna 'assigned_delivery_point_id' ya existe en 'user'. No hace falta hacer nada.")
            else:
                print(f"[ERROR] {e}")
                sys.exit(1)

if __name__ == "__main__":
    main()
