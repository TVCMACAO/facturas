#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para crear el primer Super Administrador del sistema.
Ejecutar: python create_super_admin.py
"""
import sys
from getpass import getpass

from app import create_app, db
from app.models import User, Company, CompanyConfig, Role

def create_super_admin():
    """Crea un Super Administrador"""
    app = create_app()
    
    with app.app_context():
        role_super = Role.query.filter_by(code='super_admin').first()
        if not role_super:
            print("[ERROR] No existe el rol 'super_admin' en la tabla roles. Ejecute antes la migración: migrate_roles_table.sql o python migrate_roles_table.py")
            return
        # Verificar si ya existe un super-admin
        existing_super_admin = User.query.filter_by(role_id=role_super.id).first()
        if existing_super_admin:
            print(f"\n[ADVERTENCIA] Ya existe un Super Administrador: {existing_super_admin.username}")
            response = input("¿Desea crear otro Super Administrador? (s/n): ").lower()
            if response != 's':
                print("Operación cancelada.")
                return
        
        # Solicitar información
        print("\n=== Crear Super Administrador ===")
        print("El Super Administrador necesita una empresa asociada.")
        print("Si no existe una empresa, se creará una automáticamente.\n")
        
        name = input("Nombre completo: ").strip()
        if not name:
            print("[ERROR] El nombre es requerido.")
            return
        
        username = input("Nombre de usuario: ").strip()
        if not username:
            print("[ERROR] El nombre de usuario es requerido.")
            return
        
        # Verificar si el username ya existe
        if User.query.filter_by(username=username).first():
            print(f"[ERROR] El usuario '{username}' ya existe.")
            return
        
        email = input("Email: ").strip()
        if not email:
            print("[ERROR] El email es requerido.")
            return
        
        # Verificar si el email ya existe
        if User.query.filter_by(email=email).first():
            print(f"[ERROR] El email '{email}' ya está registrado.")
            return
        
        password = getpass("Contraseña: ").strip()
        if len(password) < 6:
            print("[ERROR] La contraseña debe tener al menos 6 caracteres.")
            return
        
        password2 = getpass("Repetir contraseña: ").strip()
        if password != password2:
            print("[ERROR] Las contraseñas no coinciden.")
            return
        
        # Crear o usar empresa existente
        company_name = input("Nombre de la empresa (o presione Enter para usar 'Sistema'): ").strip()
        if not company_name:
            company_name = "Sistema"
        
        # Buscar empresa existente o crear una nueva
        company = Company.query.filter_by(name=company_name).first()
        if not company:
            print(f"\nCreando empresa '{company_name}'...")
            company = Company(
                name=company_name,
                active=True
            )
            db.session.add(company)
            db.session.flush()
            
            # Crear configuración por defecto
            config = CompanyConfig(
                company_id=company.id,
                default_tax_rate=19.0,
                monthly_sales_target=10000.0,
                quote_number_prefix='COT',
                invoice_number_prefix='FAC',
                credit_note_number_prefix='NC'
            )
            db.session.add(config)
        else:
            print(f"\nUsando empresa existente: {company.name}")
        
        # Crear Super Administrador
        print("\nCreando Super Administrador...")
        super_admin = User(
            name=name,
            username=username,
            email=email,
            company_id=company.id,
            role_id=role_super.id,
            active=True
        )
        super_admin.set_password(password)
        db.session.add(super_admin)
        db.session.flush()
        
        # Asignar created_by a la empresa si no tiene
        if not company.created_by:
            company.created_by = super_admin.id
        
        try:
            db.session.commit()
            print("\n[OK] Super Administrador creado exitosamente!")
            print(f"\nDetalles:")
            print(f"  - Usuario: {username}")
            print(f"  - Email: {email}")
            print(f"  - Empresa: Ninguna (puede gestionar todas las empresas)")
            print(f"  - Rol: Super Administrador")
            print(f"\nPuede iniciar sesión con estas credenciales.")
        except Exception as e:
            db.session.rollback()
            print(f"\n[ERROR] No se pudo crear el Super Administrador: {e}")
            return

if __name__ == '__main__':
    try:
        create_super_admin()
    except KeyboardInterrupt:
        print("\n\nOperación cancelada por el usuario.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Error inesperado: {e}")
        sys.exit(1)
