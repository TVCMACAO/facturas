"""
Script de migración para actualizar la base de datos con las nuevas columnas.
Ejecuta este script para agregar las columnas faltantes a las tablas existentes.
"""

import sys
import json
import time
from sqlalchemy import text, inspect
from app import create_app, db
from app.models import Quote, Invoice, InventoryMovement, CreditNote, CreditNoteItem, AuditLog, PasswordResetToken, Company, CompanyConfig, User, Client, Product, Warehouse, ProductWarehouseStock, DeliveryPoint

LOG_PATH = r"e:\DESCARGAS ACTUALES\CLAUDE\PROYECTOS EN PY\CUENTAS DE COBRO\.cursor\debug.log"

def log_debug(location, message, data=None, hypothesis_id=None):
    """Escribe un log en formato NDJSON"""
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            log_entry = {
                "timestamp": int(time.time() * 1000),
                "location": location,
                "message": message,
                "data": data or {},
                "sessionId": "migration-debug",
                "hypothesisId": hypothesis_id
            }
            f.write(json.dumps(log_entry) + "\n")
    except:
        pass

def migrate_database():
    """Agrega las nuevas columnas y tablas a la base de datos."""
    
    print("=" * 60)
    print("SCRIPT DE MIGRACIÓN DE BASE DE DATOS")
    print("=" * 60)
    print("Este script DEBE ejecutarse desde la línea de comandos con:")
    print("  python migrate_database.py")
    print("NO lo ejecutes desde phpMyAdmin o herramientas SQL")
    print("=" * 60)
    print()
    
    try:
        app = create_app()
    except Exception as e:
        print(f"[ERROR] No se pudo crear la aplicación Flask: {e}")
        sys.exit(1)
    
    with app.app_context():
        print("Iniciando migración de base de datos...")
        
        # Verificar conexión a la base de datos
        try:
            with db.engine.connect() as conn:
                conn.execute(db.text("SELECT 1"))
            print("[OK] Conexión a la base de datos verificada")
        except Exception as e:
            print(f"[ERROR] No se pudo conectar a la base de datos: {e}")
            print("Verifica la configuración en config.py")
            sys.exit(1)
        
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
            
            # Agregar contact_person a company si no existe
            try:
                with db.engine.connect() as conn:
                    conn.execute(db.text("""
                        ALTER TABLE company 
                        ADD COLUMN contact_person VARCHAR(128) NULL AFTER website
                    """))
                    conn.commit()
                print("[OK] Columna 'contact_person' agregada a 'company'")
            except Exception as e:
                if "Duplicate column name" in str(e) or "already exists" in str(e):
                    print("[INFO] Columna 'contact_person' ya existe en 'company'")
                else:
                    print(f"[ADVERTENCIA] Error al agregar 'contact_person' a 'company': {e}")
            
            # Agregar columnas a product: barcode, unit_of_sale, units_per_package
            for col_name, col_def in [
                ('barcode', 'VARCHAR(100) NULL'),
                ('unit_of_sale', "VARCHAR(20) DEFAULT 'unidad'"),
                ('units_per_package', 'INT NULL'),
            ]:
                try:
                    with db.engine.connect() as conn:
                        conn.execute(db.text(f"""
                            ALTER TABLE product ADD COLUMN {col_name} {col_def}
                        """))
                        conn.commit()
                    print(f"[OK] Columna '{col_name}' agregada a 'product'")
                except Exception as e:
                    if "Duplicate column name" in str(e) or "already exists" in str(e):
                        print(f"[INFO] Columna '{col_name}' ya existe en 'product'")
                    else:
                        print(f"[ADVERTENCIA] Error al agregar '{col_name}' a 'product': {e}")
            
            # Crear nuevas tablas (warehouse, delivery_point, product_warehouse_stock, delivery, etc.)
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
            
            # Agregar columna 'active' a la tabla 'user' si no existe
            try:
                with db.engine.connect() as conn:
                    conn.execute(db.text("""
                        ALTER TABLE user 
                        ADD COLUMN active BOOLEAN NOT NULL DEFAULT TRUE
                    """))
                    conn.commit()
                print("[OK] Columna 'active' agregada a 'user'")
            except Exception as e:
                if "Duplicate column name" in str(e) or "already exists" in str(e) or "Duplicate column" in str(e):
                    print("[INFO] Columna 'active' ya existe en 'user'")
                else:
                    print(f"[ADVERTENCIA] Error al agregar 'active' a 'user': {e}")
            
            # Establecer todos los usuarios existentes como activos si el campo existe
            try:
                with db.engine.connect() as conn:
                    result = conn.execute(db.text("""
                        UPDATE user 
                        SET active = TRUE 
                        WHERE active IS NULL OR active = FALSE
                    """))
                    conn.commit()
                    if result.rowcount > 0:
                        print(f"[OK] Actualizados {result.rowcount} usuarios existentes como activos")
            except Exception as e:
                print(f"[INFO] No se pudieron actualizar usuarios existentes: {e}")
            
            # Agregar columnas para despachador y bodega del almacén (ANTES de usar User/DeliveryPoint en el resto de la migración)
            for table_name, col_name, col_def in [
                ('delivery_point', 'warehouse_id', 'INT NULL'),
                ('user', 'assigned_delivery_point_id', 'INT NULL'),
            ]:
                try:
                    inspector = inspect(db.engine)
                    if table_name not in inspector.get_table_names():
                        print(f"[INFO] Tabla '{table_name}' aún no existe, se creará después con create_all()")
                        continue
                    existing_columns = [c['name'] for c in inspector.get_columns(table_name)]
                    if col_name in existing_columns:
                        print(f"[INFO] Columna '{col_name}' ya existe en '{table_name}'")
                    else:
                        with db.engine.connect() as conn:
                            conn.execute(text(f"ALTER TABLE `{table_name}` ADD COLUMN `{col_name}` {col_def}"))
                            conn.commit()
                        print(f"[OK] Columna '{col_name}' agregada a '{table_name}'")
                except Exception as e:
                    if "Duplicate column" in str(e) or "already exists" in str(e):
                        print(f"[INFO] Columna '{col_name}' ya existe en '{table_name}'")
                    else:
                        print(f"[ADVERTENCIA] Error al agregar '{col_name}' a '{table_name}': {e}")
            
            # ========== MIGRACIÓN MULTI-TENANT ==========
            print("\n=== Iniciando migración Multi-Tenant ===")
            
            # 1. Crear tablas Company y CompanyConfig
            db.create_all()
            print("[OK] Tablas Company y CompanyConfig creadas (si no existían)")
            
            # 2. Verificar si ya existe una empresa
            existing_company = Company.query.first()
            if existing_company:
                print(f"[INFO] Ya existe una empresa: {existing_company.name}. Saltando creación de empresa inicial.")
            else:
                # 3. Crear primera empresa con datos por defecto
                print("[INFO] Creando primera empresa con datos existentes...")
                first_company = Company(
                    name="Mi Empresa",
                    active=True
                )
                db.session.add(first_company)
                db.session.flush()
                print(f"[OK] Empresa creada con ID: {first_company.id}")
                
                # 4. Crear CompanyConfig para la primera empresa
                company_config = CompanyConfig(
                    company_id=first_company.id,
                    default_tax_rate=19.0,
                    monthly_sales_target=10000.0,
                    quote_number_prefix='COT',
                    invoice_number_prefix='FAC',
                    credit_note_number_prefix='NC'
                )
                db.session.add(company_config)
                print("[OK] Configuración de empresa creada")
                
                # 5. Agregar company_id a todas las tablas existentes
                tables_to_migrate = [
                    ('user', 'company_id', 'INTEGER NOT NULL'),
                    ('client', 'company_id', 'INTEGER NOT NULL'),
                    ('product', 'company_id', 'INTEGER NOT NULL'),
                    ('quote', 'company_id', 'INTEGER NOT NULL'),
                    ('invoice', 'company_id', 'INTEGER NOT NULL'),
                    ('credit_note', 'company_id', 'INTEGER NOT NULL')
                ]
                
                for table_name, col_name, col_type in tables_to_migrate:
                    try:
                        # Verificar si la columna ya existe
                        inspector = inspect(db.engine)
                        existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
                        
                        if col_name in existing_columns:
                            print(f"[INFO] Columna '{col_name}' ya existe en '{table_name}'. Verificando datos...")
                            # Verificar si hay registros sin company_id
                            with db.engine.connect() as conn:
                                result = conn.execute(text(f"SELECT COUNT(*) as cnt FROM {table_name} WHERE {col_name} IS NULL"))
                                row = result.fetchone()
                                null_count = row[0] if row else 0
                                
                                if null_count > 0:
                                    print(f"[INFO] Actualizando {null_count} registros sin company_id...")
                                    result = conn.execute(text(f"""
                                        UPDATE {table_name} 
                                        SET {col_name} = {first_company.id}
                                        WHERE {col_name} IS NULL
                                    """))
                                    conn.commit()
                                    print(f"[OK] Actualizados {result.rowcount} registros en '{table_name}'")
                                else:
                                    print(f"[OK] Todos los registros en '{table_name}' ya tienen company_id")
                        else:
                            # La columna no existe, crearla
                            with db.engine.begin() as trans:
                                # Primero agregar la columna como nullable
                                trans.execute(text(f"""
                                    ALTER TABLE {table_name} 
                                    ADD COLUMN {col_name} INTEGER
                                """))
                                
                                # Asignar el company_id a todos los registros existentes
                                result = trans.execute(text(f"""
                                    UPDATE {table_name} 
                                    SET {col_name} = {first_company.id}
                                    WHERE {col_name} IS NULL
                                """))
                                
                                # Hacer la columna NOT NULL
                                trans.execute(text(f"""
                                    ALTER TABLE {table_name} 
                                    MODIFY COLUMN {col_name} {col_type}
                                """))
                                
                                # Agregar índice
                                try:
                                    trans.execute(text(f"""
                                        CREATE INDEX idx_{table_name}_{col_name} ON {table_name}({col_name})
                                    """))
                                except Exception as idx_error:
                                    # El índice puede ya existir
                                    pass
                            
                            print(f"[OK] Columna '{col_name}' agregada a '{table_name}' y datos migrados")
                    except Exception as e:
                        if "Duplicate column name" in str(e) or "already exists" in str(e) or "Duplicate column" in str(e):
                            print(f"[INFO] Columna '{col_name}' ya existe en '{table_name}'")
                        else:
                            print(f"[ADVERTENCIA] Error al agregar '{col_name}' a '{table_name}': {e}")
                
                # 6. Asignar created_by a la empresa (usar el primer usuario admin o el primero disponible)
                first_user = User.query.first()
                if first_user:
                    first_company.created_by = first_user.id
                    db.session.commit()
                    print(f"[OK] Usuario {first_user.username} asignado como creador de la empresa")
                
                db.session.commit()
                print("[OK] Migración Multi-Tenant completada exitosamente")
            
            # Bodega por defecto y ProductWarehouseStock por empresa
            for company in Company.query.all():
                default_warehouse = Warehouse.query.filter_by(company_id=company.id).first()
                if not default_warehouse:
                    default_warehouse = Warehouse(
                        company_id=company.id,
                        name='Principal',
                        warehouse_type='minorista',
                        active=True
                    )
                    db.session.add(default_warehouse)
                    db.session.flush()
                    print(f"[OK] Bodega 'Principal' creada para empresa {company.name} (id={company.id})")
                for product in Product.query.filter_by(company_id=company.id).all():
                    pws = ProductWarehouseStock.query.filter_by(
                        product_id=product.id,
                        warehouse_id=default_warehouse.id
                    ).first()
                    if not pws:
                        pws = ProductWarehouseStock(
                            product_id=product.id,
                            warehouse_id=default_warehouse.id,
                            quantity=product.stock or 0
                        )
                        db.session.add(pws)
                db.session.commit()
            print("[OK] Bodegas por defecto y stock inicial verificados")

            # Almacén de entrega por defecto por empresa
            for company in Company.query.all():
                default_delivery_point = DeliveryPoint.query.filter_by(company_id=company.id).first()
                minorista = Warehouse.query.filter_by(company_id=company.id, warehouse_type='minorista', active=True).first()
                if not default_delivery_point:
                    default_delivery_point = DeliveryPoint(
                        company_id=company.id,
                        name='Almacén de Entrega Principal',
                        code='ENT-01',
                        address='',
                        active=True,
                        warehouse_id=minorista.id if minorista else None
                    )
                    db.session.add(default_delivery_point)
                    db.session.flush()
                    print(f"[OK] Almacén de entrega 'Almacén de Entrega Principal' creado para empresa {company.name} (id={company.id})")
                elif minorista and getattr(default_delivery_point, 'warehouse_id', None) is None:
                    default_delivery_point.warehouse_id = minorista.id
                    print(f"[OK] Bodega minorista asignada al almacén de entrega para {company.name}")
            db.session.commit()
            print("[OK] Almacenes de entrega por defecto verificados")

            # Opcional: unificar rol despachador → minorista (mismo permiso, nombre estándar)
            try:
                from app.models import User
                n = User.query.filter_by(role='despachador').update({'role': 'minorista'})
                if n:
                    db.session.commit()
                    print(f"[OK] {n} usuario(s) con rol 'despachador' actualizado(s) a 'minorista'")
            except Exception as e:
                if "Duplicate column" not in str(e):
                    print(f"[INFO] Migración despachador→minorista: {e}")

            print("\n[COMPLETADO] Migración de base de datos finalizada exitosamente!")
            
        except Exception as e:
            print(f"\n[ERROR] Error durante la migración: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    migrate_database()
