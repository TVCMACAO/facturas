"""
Script de verificación para comprobar que la migración se aplicó correctamente
"""

from app import create_app, db
from app.models import Company, CompanyConfig, User, Client, Product, Quote, Invoice

def verify_migration():
    """Verifica que todas las columnas y tablas necesarias existan"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("VERIFICACIÓN DE MIGRACIÓN")
        print("=" * 60)
        print()
        
        errors = []
        warnings = []
        
        # Verificar tablas Company y CompanyConfig
        try:
            company_count = Company.query.count()
            print(f"✓ Tabla 'company' existe: {company_count} empresa(s) encontrada(s)")
            
            if company_count == 0:
                warnings.append("No hay empresas creadas. Se creará una automáticamente al registrar el primer usuario.")
        except Exception as e:
            errors.append(f"✗ Error al acceder a tabla 'company': {e}")
        
        try:
            config_count = CompanyConfig.query.count()
            print(f"✓ Tabla 'company_config' existe: {config_count} configuración(es) encontrada(s)")
        except Exception as e:
            errors.append(f"✗ Error al acceder a tabla 'company_config': {e}")
        
        # Verificar columnas en User
        try:
            user = User.query.first()
            if user:
                has_company_id = hasattr(user, 'company_id') and user.company_id is not None
                has_active = hasattr(user, 'active') and user.active is not None
                
                if has_company_id:
                    print(f"✓ Columna 'company_id' existe en 'user': {user.company_id}")
                else:
                    errors.append("✗ Columna 'company_id' no existe o es NULL en 'user'")
                
                if has_active:
                    print(f"✓ Columna 'active' existe en 'user': {user.active}")
                else:
                    errors.append("✗ Columna 'active' no existe en 'user'")
            else:
                warnings.append("No hay usuarios en la base de datos")
        except Exception as e:
            errors.append(f"✗ Error al verificar 'user': {e}")
        
        # Verificar columnas en Quote
        try:
            quote = Quote.query.first()
            if quote:
                has_subtotal = hasattr(quote, 'subtotal')
                has_company_id = hasattr(quote, 'company_id') and quote.company_id is not None
                
                if has_subtotal:
                    print(f"✓ Columna 'subtotal' existe en 'quote'")
                else:
                    errors.append("✗ Columna 'subtotal' no existe en 'quote'")
                
                if has_company_id:
                    print(f"✓ Columna 'company_id' existe en 'quote': {quote.company_id}")
                else:
                    errors.append("✗ Columna 'company_id' no existe o es NULL en 'quote'")
            else:
                warnings.append("No hay cotizaciones en la base de datos")
        except Exception as e:
            errors.append(f"✗ Error al verificar 'quote': {e}")
        
        # Verificar columnas en Invoice
        try:
            invoice = Invoice.query.first()
            if invoice:
                has_subtotal = hasattr(invoice, 'subtotal')
                has_company_id = hasattr(invoice, 'company_id') and invoice.company_id is not None
                
                if has_subtotal:
                    print(f"✓ Columna 'subtotal' existe en 'invoice'")
                else:
                    errors.append("✗ Columna 'subtotal' no existe en 'invoice'")
                
                if has_company_id:
                    print(f"✓ Columna 'company_id' existe en 'invoice': {invoice.company_id}")
                else:
                    errors.append("✗ Columna 'company_id' no existe o es NULL en 'invoice'")
            else:
                warnings.append("No hay facturas en la base de datos")
        except Exception as e:
            errors.append(f"✗ Error al verificar 'invoice': {e}")
        
        # Verificar que todos los registros tengan company_id
        try:
            null_users = User.query.filter(User.company_id == None).count()
            null_clients = Client.query.filter(Client.company_id == None).count()
            null_products = Product.query.filter(Product.company_id == None).count()
            null_quotes = Quote.query.filter(Quote.company_id == None).count()
            null_invoices = Invoice.query.filter(Invoice.company_id == None).count()
            
            if null_users == 0 and null_clients == 0 and null_products == 0 and null_quotes == 0 and null_invoices == 0:
                print("✓ Todos los registros tienen company_id asignado")
            else:
                if null_users > 0:
                    errors.append(f"✗ {null_users} usuario(s) sin company_id")
                if null_clients > 0:
                    errors.append(f"✗ {null_clients} cliente(s) sin company_id")
                if null_products > 0:
                    errors.append(f"✗ {null_products} producto(s) sin company_id")
                if null_quotes > 0:
                    errors.append(f"✗ {null_quotes} cotización(es) sin company_id")
                if null_invoices > 0:
                    errors.append(f"✗ {null_invoices} factura(s) sin company_id")
        except Exception as e:
            errors.append(f"✗ Error al verificar company_id en registros: {e}")
        
        print()
        print("=" * 60)
        
        if warnings:
            print("\nADVERTENCIAS:")
            for warning in warnings:
                print(f"  ⚠ {warning}")
        
        if errors:
            print("\nERRORES ENCONTRADOS:")
            for error in errors:
                print(f"  {error}")
            print("\n✗ La migración NO se completó correctamente")
            return False
        else:
            print("\n✓ VERIFICACIÓN EXITOSA: La migración se aplicó correctamente")
            if warnings:
                print("  (Algunas advertencias menores fueron encontradas, pero no son críticas)")
            return True

if __name__ == '__main__':
    try:
        success = verify_migration()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Error durante la verificación: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
