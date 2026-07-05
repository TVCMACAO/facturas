"""
Script de prueba para verificar las funciones de usuarios y compañías
"""

from app import create_app, db
from app.models import Company, CompanyConfig, User, Client, Product, Quote, Invoice
from app.tenant import get_current_company_id, filter_by_company, ensure_company_id
from werkzeug.security import generate_password_hash
import sys

def test_company_creation():
    """Prueba la creación de una nueva compañía con usuario"""
    print("=" * 60)
    print("PRUEBA 1: Creación de Compañía y Usuario")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        try:
            # Simular el proceso de registro
            # 1. Crear empresa
            company = Company(
                name="Empresa de Prueba",
                active=True
            )
            db.session.add(company)
            db.session.flush()  # Para obtener el ID
            
            print(f"[OK] Empresa creada con ID: {company.id}")
            
            # 2. Crear configuración
            company_config = CompanyConfig(
                company_id=company.id,
                default_tax_rate=19.0,
                monthly_sales_target=10000.0,
                quote_number_prefix='COT',
                invoice_number_prefix='FAC',
                credit_note_number_prefix='NC'
            )
            db.session.add(company_config)
            print("[OK] Configuracion de empresa creada")
            
            # 3. Crear usuario
            user = User(
                name="Usuario de Prueba",
                username="test_user",
                email="test@example.com",
                company_id=company.id,
                role='admin',
                active=True
            )
            user.set_password("test123")
            db.session.add(user)
            db.session.flush()  # Para obtener el ID del usuario
            
            print(f"[OK] Usuario creado con ID: {user.id}, company_id: {user.company_id}")
            
            # 4. Asignar created_by
            company.created_by = user.id
            print(f"[OK] created_by asignado: {company.created_by}")
            
            # Hacer rollback para no dejar datos de prueba
            db.session.rollback()
            print("[OK] Rollback realizado (datos de prueba no guardados)")
            
            return True
        except Exception as e:
            print(f"[ERROR] Error: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False

def test_company_isolation():
    """Prueba que los datos estén aislados por compañía"""
    print("\n" + "=" * 60)
    print("PRUEBA 2: Aislamiento de Datos por Compañía")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        try:
            # Obtener todas las compañías
            companies = Company.query.all()
            print(f"[OK] Compañías encontradas: {len(companies)}")
            
            if len(companies) < 2:
                print("[ADVERTENCIA] Se necesitan al menos 2 compañías para probar el aislamiento")
                return True
            
            # Verificar usuarios por compañía
            for company in companies:
                users = User.query.filter_by(company_id=company.id).all()
                print(f"  - {company.name}: {len(users)} usuario(s)")
                
                # Verificar que los usuarios tienen el company_id correcto
                for user in users:
                    if user.company_id != company.id:
                        print(f"[ERROR] ERROR: Usuario {user.username} tiene company_id incorrecto")
                        return False
            
            print("[OK] Aislamiento de usuarios verificado")
            
            # Verificar clientes por compañía
            for company in companies:
                clients = Client.query.filter_by(company_id=company.id).all()
                print(f"  - {company.name}: {len(clients)} cliente(s)")
                
                for client in clients:
                    if client.company_id != company.id:
                        print(f"[ERROR] ERROR: Cliente {client.name} tiene company_id incorrecto")
                        return False
            
            print("[OK] Aislamiento de clientes verificado")
            
            return True
        except Exception as e:
            print(f"[ERROR] Error: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_filter_by_company():
    """Prueba la función filter_by_company"""
    print("\n" + "=" * 60)
    print("PRUEBA 3: Función filter_by_company")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        try:
            # Obtener primera compañía
            company = Company.query.first()
            if not company:
                print("[ADVERTENCIA] No hay compañías en la base de datos")
                return True
            
            # Simular un usuario autenticado
            user = User.query.filter_by(company_id=company.id).first()
            if not user:
                print("[ADVERTENCIA] No hay usuarios en la primera compañía")
                return True
            
            # Usar Flask-Login para simular usuario autenticado
            from flask_login import login_user
            with app.test_request_context():
                login_user(user)
                
                # Probar filter_by_company
                client_query = filter_by_company(Client.query, Client)
                clients = client_query.all()
                
                print(f"[OK] Usuario {user.username} (company_id: {user.company_id})")
                print(f"[OK] Clientes filtrados: {len(clients)}")
                
                # Verificar que todos los clientes pertenecen a la misma compañía
                for client in clients:
                    if client.company_id != user.company_id:
                        print(f"[ERROR] ERROR: Cliente {client.name} no pertenece a la compañía del usuario")
                        return False
                
                print("[OK] Todos los clientes pertenecen a la compañía correcta")
            
            return True
        except Exception as e:
            print(f"[ERROR] Error: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_ensure_company_id():
    """Prueba la función ensure_company_id"""
    print("\n" + "=" * 60)
    print("PRUEBA 4: Función ensure_company_id")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        try:
            # Obtener primera compañía y usuario
            company = Company.query.first()
            if not company:
                print("[ADVERTENCIA] No hay compañías en la base de datos")
                return True
            
            user = User.query.filter_by(company_id=company.id).first()
            if not user:
                print("[ADVERTENCIA] No hay usuarios en la primera compañía")
                return True
            
            # Obtener un cliente de la misma compañía
            client = Client.query.filter_by(company_id=company.id).first()
            if not client:
                print("[ADVERTENCIA] No hay clientes en la primera compañía")
                return True
            
            # Simular usuario autenticado
            from flask_login import login_user
            with app.test_request_context():
                login_user(user)
                
                # Probar ensure_company_id con un cliente de la misma compañía
                try:
                    verified_client = ensure_company_id(client.id, Client)
                    print(f"[OK] Cliente {verified_client.name} verificado correctamente")
                except Exception as e:
                    print(f"[ERROR] ERROR al verificar cliente: {e}")
                    return False
                
                # Probar con un ID que no existe
                try:
                    ensure_company_id(999999, Client)
                    print("[ERROR] ERROR: Debería haber fallado con un ID inexistente")
                    return False
                except:
                    print("[OK] Correctamente rechazó un ID inexistente")
            
            return True
        except Exception as e:
            print(f"[ERROR] Error: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_user_registration_flow():
    """Prueba el flujo completo de registro de usuario"""
    print("\n" + "=" * 60)
    print("PRUEBA 5: Flujo de Registro de Usuario")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        try:
            # Contar compañías antes
            companies_before = Company.query.count()
            users_before = User.query.count()
            
            print(f"Estado inicial: {companies_before} compañía(s), {users_before} usuario(s)")
            
            # Simular registro (sin guardar)
            company = Company(
                name="Nueva Empresa Test",
                active=True
            )
            db.session.add(company)
            db.session.flush()
            
            company_config = CompanyConfig(
                company_id=company.id,
                default_tax_rate=19.0,
                monthly_sales_target=10000.0,
                quote_number_prefix='COT',
                invoice_number_prefix='FAC',
                credit_note_number_prefix='NC'
            )
            db.session.add(company_config)
            
            user = User(
                name="Nuevo Usuario",
                username="nuevo_usuario",
                email="nuevo@example.com",
                company_id=company.id,
                role='admin',
                active=True
            )
            user.set_password("password123")
            db.session.add(user)
            db.session.flush()
            
            company.created_by = user.id
            
            print(f"[OK] Empresa creada: {company.name} (ID: {company.id})")
            print(f"[OK] Configuración creada para empresa {company.id}")
            print(f"[OK] Usuario creado: {user.username} (ID: {user.id}, company_id: {user.company_id})")
            print(f"[OK] created_by asignado: {company.created_by}")
            
            # Verificar relaciones
            if user.company_id == company.id:
                print("[OK] Relación usuario-empresa correcta")
            else:
                print("[ERROR] ERROR: Relación usuario-empresa incorrecta")
                db.session.rollback()
                return False
            
            if company.created_by == user.id:
                print("[OK] Relación empresa-creador correcta")
            else:
                print("[ERROR] ERROR: Relación empresa-creador incorrecta")
                db.session.rollback()
                return False
            
            # Rollback
            db.session.rollback()
            print("[OK] Rollback realizado (datos de prueba no guardados)")
            
            return True
        except Exception as e:
            print(f"[ERROR] Error: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False

def main():
    """Ejecuta todas las pruebas"""
    print("\n" + "=" * 60)
    print("VERIFICACIÓN DE FUNCIONES PARA USUARIOS Y COMPAÑÍAS")
    print("=" * 60)
    print()
    
    results = []
    
    results.append(("Creación de Compañía y Usuario", test_company_creation()))
    results.append(("Aislamiento de Datos por Compañía", test_company_isolation()))
    results.append(("Función filter_by_company", test_filter_by_company()))
    results.append(("Función ensure_company_id", test_ensure_company_id()))
    results.append(("Flujo de Registro de Usuario", test_user_registration_flow()))
    
    print("\n" + "=" * 60)
    print("RESUMEN DE PRUEBAS")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "[OK] PASÓ" if result else "[ERROR] FALLÓ"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print()
    print(f"Total: {passed} pasaron, {failed} fallaron")
    print("=" * 60)
    
    if failed == 0:
        print("\n[OK] TODAS LAS PRUEBAS PASARON")
        return 0
    else:
        print(f"\n[ERROR] {failed} PRUEBA(S) FALLARON")
        return 1

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n[ERROR] Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
