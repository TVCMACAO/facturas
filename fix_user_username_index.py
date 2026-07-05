"""
Script para corregir la tabla user en MySQL.
Elimina el índice único antiguo 'ix_user_username' que impedía repetir el mismo
nombre de usuario en distintas empresas. La aplicación usa unicidad por (company_id, username).

Ejecutar: python fix_user_username_index.py
"""

import sys
from app import create_app, db


def fix_user_table():
    print("=" * 60)
    print("CORRECCIÓN ÍNDICE user.ix_user_username")
    print("=" * 60)
    print("Permite que el mismo username exista en distintas empresas.")
    print()

    try:
        app = create_app()
    except Exception as e:
        print(f"[ERROR] No se pudo crear la aplicación: {e}")
        sys.exit(1)

    with app.app_context():
        try:
            with db.engine.connect() as conn:
                conn.execute(db.text("DROP INDEX ix_user_username ON user"))
                conn.commit()
            print("[OK] Índice ix_user_username eliminado correctamente.")
            print("     Ahora puedes crear usuarios con el mismo nombre en distintas empresas.")
        except Exception as e:
            err_str = str(e).lower()
            if "1091" in err_str or "can't drop" in err_str or "check that it exists" in err_str:
                print("[INFO] El índice ix_user_username no existe (ya fue eliminado o nunca existió).")
                print("       No es necesario hacer nada.")
            else:
                print(f"[ERROR] No se pudo eliminar el índice: {e}")
                sys.exit(1)
    print()
    print("Listo.")


if __name__ == "__main__":
    fix_user_table()
