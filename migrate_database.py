"""
Script de migración para actualizar la base de datos con las nuevas columnas.
Ejecuta este script para agregar las columnas faltantes a las tablas existentes.
"""

import sys
from app import create_app, db
from app.models import Quote, Invoice, InventoryMovement, CreditNote, CreditNoteItem, AuditLog, PasswordResetToken

def migrate_database():
    """Agrega las nuevas columnas y tablas a la base de datos."""
    app = create_app()
    
    with app.app_context():
        print("Iniciando migración de base de datos...")
        
        try:
            # Intentar agregar columnas a quote si no existen
            try:
                with db.engine.connect() as conn:
                    conn.execute(db.text("""
                        ALTER TABLE quote 
                        ADD COLUMN subtotal FLOAT NOT NULL DEFAULT 0.0 AFTER client_id
                    """))
                    conn.commit()
                print("[OK] Columna 'subtotal' agregada a 'quote'")
            except Exception as e:
                if "Duplicate column name" in str(e) or "already exists" in str(e):
                    print("[INFO] Columna 'subtotal' ya existe en 'quote'")
                else:
                    print(f"[ADVERTENCIA] Error al agregar 'subtotal' a 'quote': {e}")
            
            columns_quote = [
                ("discount_type", "VARCHAR(20) DEFAULT 'none'"),
                ("discount_value", "FLOAT NOT NULL DEFAULT 0.0"),
                ("discount_amount", "FLOAT NOT NULL DEFAULT 0.0"),
                ("tax_rate", "FLOAT NOT NULL DEFAULT 0.0"),
                ("tax_amount", "FLOAT NOT NULL DEFAULT 0.0")
            ]
            
            for col_name, col_def in columns_quote:
                try:
                    with db.engine.connect() as conn:
                        prev_col = columns_quote[columns_quote.index((col_name, col_def)) - 1][0] if columns_quote.index((col_name, col_def)) > 0 else "subtotal"
                        conn.execute(db.text(f"""
                            ALTER TABLE quote 
                            ADD COLUMN {col_name} {col_def} AFTER {prev_col}
                        """))
                        conn.commit()
                    print(f"[OK] Columna '{col_name}' agregada a 'quote'")
                except Exception as e:
                    if "Duplicate column name" in str(e) or "already exists" in str(e):
                        print(f"[INFO] Columna '{col_name}' ya existe en 'quote'")
                    else:
                        print(f"[ADVERTENCIA] Error al agregar '{col_name}' a 'quote': {e}")
            
            # Agregar columnas a invoice
            try:
                with db.engine.connect() as conn:
                    conn.execute(db.text("""
                        ALTER TABLE invoice 
                        ADD COLUMN subtotal FLOAT NOT NULL DEFAULT 0.0 AFTER quote_id
                    """))
                    conn.commit()
                print("[OK] Columna 'subtotal' agregada a 'invoice'")
            except Exception as e:
                if "Duplicate column name" in str(e) or "already exists" in str(e):
                    print("[INFO] Columna 'subtotal' ya existe en 'invoice'")
                else:
                    print(f"[ADVERTENCIA] Error al agregar 'subtotal' a 'invoice': {e}")
            
            columns_invoice = [
                ("discount_type", "VARCHAR(20) DEFAULT 'none'"),
                ("discount_value", "FLOAT NOT NULL DEFAULT 0.0"),
                ("discount_amount", "FLOAT NOT NULL DEFAULT 0.0"),
                ("tax_rate", "FLOAT NOT NULL DEFAULT 0.0"),
                ("tax_amount", "FLOAT NOT NULL DEFAULT 0.0")
            ]
            
            for col_name, col_def in columns_invoice:
                try:
                    with db.engine.connect() as conn:
                        prev_col = columns_invoice[columns_invoice.index((col_name, col_def)) - 1][0] if columns_invoice.index((col_name, col_def)) > 0 else "subtotal"
                        conn.execute(db.text(f"""
                            ALTER TABLE invoice 
                            ADD COLUMN {col_name} {col_def} AFTER {prev_col}
                        """))
                        conn.commit()
                    print(f"[OK] Columna '{col_name}' agregada a 'invoice'")
                except Exception as e:
                    if "Duplicate column name" in str(e) or "already exists" in str(e):
                        print(f"[INFO] Columna '{col_name}' ya existe en 'invoice'")
                    else:
                        print(f"[ADVERTENCIA] Error al agregar '{col_name}' a 'invoice': {e}")
            
            # Crear nuevas tablas
            db.create_all()
            print("[OK] Nuevas tablas creadas (si no existían)")
            
            # Verificar y crear tabla password_reset_token si no existe
            try:
                from sqlalchemy import inspect
                inspector = inspect(db.engine)
                existing_tables = inspector.get_table_names()
                
                if 'password_reset_token' not in existing_tables:
                    print("[INFO] Creando tabla 'password_reset_token'...")
                    db.create_all()
                    print("[OK] Tabla 'password_reset_token' creada")
                else:
                    print("[INFO] Tabla 'password_reset_token' ya existe")
            except Exception as e:
                print(f"[ADVERTENCIA] Error al verificar/crear tabla 'password_reset_token': {e}")
                # Intentar crear de todas formas
                try:
                    db.create_all()
                    print("[OK] Tabla 'password_reset_token' creada mediante create_all()")
                except Exception as e2:
                    print(f"[ERROR] No se pudo crear la tabla 'password_reset_token': {e2}")
            
            # Actualizar valores existentes
            try:
                with db.engine.connect() as conn:
                    result = conn.execute(db.text("""
                        UPDATE quote 
                        SET subtotal = total_amount,
                            tax_rate = 0.0,
                            tax_amount = 0.0
                        WHERE subtotal = 0.0 AND total_amount > 0
                    """))
                    conn.commit()
                    print(f"[OK] Actualizadas {result.rowcount} cotizaciones existentes")
            except Exception as e:
                print(f"[ADVERTENCIA] Error al actualizar cotizaciones: {e}")
            
            try:
                with db.engine.connect() as conn:
                    result = conn.execute(db.text("""
                        UPDATE invoice 
                        SET subtotal = total_amount,
                            tax_rate = 0.0,
                            tax_amount = 0.0
                        WHERE subtotal = 0.0 AND total_amount > 0
                    """))
                    conn.commit()
                    print(f"[OK] Actualizadas {result.rowcount} facturas existentes")
            except Exception as e:
                print(f"[ADVERTENCIA] Error al actualizar facturas: {e}")
            
            print("\n[COMPLETADO] Migración de base de datos finalizada exitosamente!")
            
        except Exception as e:
            print(f"\n[ERROR] Error durante la migración: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    migrate_database()
