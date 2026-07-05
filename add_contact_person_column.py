"""
Script para agregar la columna contact_person a la tabla company.
Usa la misma configuración que la aplicación (config.py).
Ejecutar desde la carpeta del proyecto: python add_contact_person_column.py
"""
import sys
from app import create_app, db

def main():
    app = create_app()
    with app.app_context():
        # Mostrar a qué base de datos se conecta (sin contraseña)
        url = db.engine.url
        db_info = f"{url.drivername}://{url.username}@{url.host}:{url.port or ''}/{url.database}"
        print(f"Conectando a: {db_info}")
        try:
            db.session.execute(db.text("""
                ALTER TABLE company 
                ADD COLUMN contact_person VARCHAR(128) NULL AFTER website
            """))
            db.session.commit()
            print("[OK] Columna 'contact_person' agregada a la tabla 'company'.")
        except Exception as e:
            err = str(e).lower()
            if "duplicate column" in err or "already exists" in err:
                print("[INFO] La columna 'contact_person' ya existe en 'company'.")
            else:
                print(f"[ERROR] {e}")
                print("\nSi la app usa otra base de datos, ejecuta este SQL en MySQL (phpMyAdmin o consola):")
                print("  ALTER TABLE company ADD COLUMN contact_person VARCHAR(128) NULL AFTER website;")
                sys.exit(1)

if __name__ == "__main__":
    main()
