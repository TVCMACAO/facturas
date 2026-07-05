from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from app import db, mail
from app.models import User, Role, AuditLog, PasswordResetToken, Company, CompanyConfig, Warehouse, DeliveryPoint, ProductWarehouseStock, Product
from app.decorators import role_required, super_admin_required, log_audit
from app.forms import AdminEditUserForm, AdminCreateUserForm, get_role_choices_from_db, CODES_BUSINESS, CODES_BUSINESS_WITH_USER, WarehouseForm, WAREHOUSE_SECTION_TYPES
from app.tenant import filter_by_company, ensure_company_id, get_current_company_id
from app.route_tokens import url_with_token
from flask_mail import Message
from datetime import datetime, timedelta
import secrets

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

WAREHOUSE_TYPE_LABELS = {'general': 'Almacén General', 'farmacia': 'Farmacia', 'mayorista': 'Almacén General', 'minorista': 'Farmacia'}

@admin_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'super_admin'])
def create_user():
    """Crea un nuevo usuario. Super-admins pueden crear en cualquier empresa y asignar rol admin.
    Admins regulares solo pueden crear usuarios con rol 'user' en su empresa."""
    from app.tenant import is_super_admin
    from app.models import Company
    from wtforms import SelectField
    from wtforms.validators import DataRequired
    
    form = AdminCreateUserForm()
    
    # Si es super-admin, agregar campo para seleccionar empresa
    if is_super_admin():
        # Agregar campo company_id dinámicamente
        companies = Company.query.order_by(Company.name).all()
        form.company_id = SelectField('Empresa', coerce=int, choices=[(c.id, c.name) for c in companies], validators=[DataRequired()])
        form.role.choices = get_role_choices_from_db(CODES_BUSINESS)
        form.role.data = 'admin'
        form.assigned_delivery_point_id.choices = [('', '-- Ninguno --')]
    else:
        form.role.choices = get_role_choices_from_db(CODES_BUSINESS)
        form.role.data = 'admin'
        delivery_points = DeliveryPoint.query.filter_by(company_id=current_user.company_id, active=True).order_by(DeliveryPoint.name).all()
        form.assigned_delivery_point_id.choices = [('', '-- Ninguno --')] + [(dp.id, dp.name) for dp in delivery_points]
    
    if form.validate_on_submit():
        # Determinar company_id
        if is_super_admin() and hasattr(form, 'company_id'):
            target_company_id = form.company_id.data
        else:
            target_company_id = current_user.company_id
        
        # Validar que solo super-admins puedan crear admins
        if form.role.data == 'admin' and not is_super_admin():
            flash('Solo los Super Administradores pueden crear administradores.', 'danger')
            return redirect(url_with_token('admin.list_users'))
        if form.role.data == 'despachador' and not form.assigned_delivery_point_id.data:
            flash('El rol Despachador requiere un punto de despacho asignado.', 'danger')
            return redirect(url_with_token('admin.create_user'))

        # Crear usuario (role_id desde tabla roles)
        role_row = Role.query.filter_by(code=form.role.data).first()
        if not role_row:
            flash('Rol no encontrado en la base de datos.', 'danger')
            return redirect(url_with_token('admin.create_user'))
        user = User(
            name=form.name.data,
            username=form.username.data,
            email=form.email.data,
            company_id=target_company_id,
            role_id=role_row.id,
            active=True,
            assigned_delivery_point_id=form.assigned_delivery_point_id.data if form.role.data == 'despachador' and form.assigned_delivery_point_id.data else None
        )
        user.set_password(form.password.data)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            err = str(e.orig) if hasattr(e, 'orig') else str(e)
            if 'ix_user_username' in err or 'Duplicate entry' in err and 'username' in err.lower():
                flash(
                    'Ese nombre de usuario ya existe en otra empresa o la base de datos tiene un índice antiguo. '
                    'Ejecuta: python fix_user_username_index.py',
                    'danger'
                )
            elif 'uq_user_company_username' in err or 'company_username' in err:
                flash('Ese nombre de usuario ya está en uso en esta empresa. Elige otro.', 'danger')
            elif 'uq_user_company_email' in err or 'company_email' in err:
                flash('Ese correo ya está en uso en esta empresa. Elige otro.', 'danger')
            else:
                flash('No se pudo crear el usuario. El usuario o el correo pueden estar duplicados.', 'danger')
            return redirect(url_with_token('admin.create_user'))
        
        flash(f'Usuario {user.username} creado exitosamente.', 'success')
        return redirect(url_with_token('admin.list_users'))
    
    return render_template('admin/create_user.html', form=form, title='Crear Usuario', is_super_admin=is_super_admin())

@admin_bp.route('/users')
@login_required
@role_required(['admin', 'super_admin'])
def list_users():
    from app.tenant import is_super_admin
    query = request.args.get('q', '').strip()
    show_inactive = request.args.get('show_inactive', 'false') == 'true' or request.args.get('status', '').strip() == 'inactivos'
    company_id_param = request.args.get('company_id', type=int)
    
    # Super_admin sin company_id debe ir a list_all_users (con token)
    if is_super_admin() and not company_id_param:
        from app.route_tokens import url_with_token
        return redirect(url_with_token('admin.list_all_users'))
    
    # Base query: por empresa. Super_admin con company_id ve usuarios de esa empresa.
    if is_super_admin() and company_id_param:
        base_query = User.query.join(User.role_rel).filter(User.company_id == company_id_param, Role.code != 'super_admin')
    else:
        base_query = filter_by_company(User.query, User).join(User.role_rel).filter(Role.code != 'super_admin')
    if not show_inactive:
        base_query = base_query.filter(User.active == True)
    
    if query:
        users = base_query.filter(
            or_(
                User.username.ilike(f'%{query}%'),
                User.name.ilike(f'%{query}%'),
                User.email.ilike(f'%{query}%')
            )
        ).order_by(User.username).all()
    else:
        users = base_query.order_by(User.username).all()
    
    return render_template(
        'admin/list_users.html',
        users=users,
        title='Administración de Usuarios',
        q=query or '',
        show_inactive=show_inactive,
        company_id=company_id_param,
        filter_q=query or '',
        filter_show_dates=False,
        filter_show_status=True,
        filter_status='inactivos' if show_inactive else '',
        filter_status_options=[('', 'Solo activos'), ('inactivos', 'Incluir inactivos')],
    )

@admin_bp.route('/users/<string:invalid_id>')
@login_required
@role_required(['admin'])
def invalid_user_id(invalid_id):
    """Maneja IDs inválidos (strings) y devuelve 404 después de verificar autenticación"""
    from flask import abort
    abort(404)

@admin_bp.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def edit_user(id):
    user = ensure_company_id(id, User)
    if user.role == 'super_admin':
        flash('No puedes editar al Super Administrador.', 'danger')
        return redirect(url_with_token('admin.list_users'))
    delivery_points = DeliveryPoint.query.filter_by(company_id=user.company_id, active=True).order_by(DeliveryPoint.name).all()
    form = AdminEditUserForm(original_username=user.username, original_email=user.email)
    # Incluir roles legacy para usuarios existentes
    form.role.choices = get_role_choices_from_db(CODES_BUSINESS_WITH_USER)
    form.assigned_delivery_point_id.choices = [('', '-- Ninguno --')] + [(dp.id, dp.name) for dp in delivery_points]
    if form.validate_on_submit():
        user.name = form.name.data
        user.username = form.username.data
        user.email = form.email.data
        user.role = form.role.data
        user.assigned_delivery_point_id = form.assigned_delivery_point_id.data if form.role.data == 'despachador' and form.assigned_delivery_point_id.data else None
        db.session.commit()
        flash('El usuario ha sido actualizado exitosamente.', 'success')
        return redirect(url_with_token('admin.list_users'))
    elif request.method == 'GET':
        form.name.data = user.name
        form.username.data = user.username
        form.email.data = user.email
        form.role.data = user.role
        form.assigned_delivery_point_id.data = user.assigned_delivery_point_id if hasattr(user, 'assigned_delivery_point_id') else None
    return render_template('admin/edit_user.html', form=form, user=user, title="Editar Usuario")

@admin_bp.route('/users/<int:id>/delete', methods=['POST'])
@login_required
@role_required(['admin'])
def delete_user(id):
    user = ensure_company_id(id, User)
    if user.role == 'super_admin':
        flash('No puedes desactivar o eliminar al Super Administrador.', 'danger')
        return redirect(url_with_token('admin.list_users'))
    if user.id == current_user.id:
        flash('No puedes eliminarte a ti mismo.', 'danger')
        return redirect(url_with_token('admin.list_users'))
    
    # Soft delete: marcar como inactivo en lugar de eliminar
    if hasattr(user, 'active'):
        user.active = False
        db.session.commit()
        log_audit('delete', 'user', user.id, {'username': user.username, 'soft': True})
        flash(f'Usuario {user.username} ha sido desactivado exitosamente.', 'success')
    else:
        # Si el campo active no existe aún, eliminar físicamente
        PasswordResetToken.query.filter_by(user_id=user.id).delete()
        AuditLog.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()
        flash(f'Usuario {user.username} eliminado exitosamente.', 'success')
    
    return redirect(url_with_token('admin.list_users'))

@admin_bp.route('/users/<int:id>/restore', methods=['POST'])
@login_required
@role_required(['admin'])
def restore_user(id):
    """Reactiva un usuario desactivado"""
    user = ensure_company_id(id, User)
    if user.role == 'super_admin':
        flash('No puedes modificar al Super Administrador.', 'danger')
        return redirect(url_with_token('admin.list_users'))
    if not hasattr(user, 'active'):
        flash('El campo active no está disponible en este usuario.', 'warning')
        return redirect(url_with_token('admin.list_users'))
    
    if user.active:
        flash('Este usuario ya está activo.', 'info')
        return redirect(url_with_token('admin.list_users'))
    
    user.active = True
    db.session.commit()
    flash(f'Usuario {user.username} ha sido reactivado exitosamente.', 'success')
    return redirect(url_with_token('admin.list_users'))

@admin_bp.route('/users/<int:id>/toggle_active', methods=['POST'])
@login_required
@role_required(['admin'])
def toggle_user_active(id):
    """Activa o desactiva un usuario (toggle)"""
    user = ensure_company_id(id, User)
    
    if user.role == 'super_admin':
        return jsonify({'success': False, 'message': 'No puedes desactivar al Super Administrador.'}), 403
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': 'No puedes desactivarte a ti mismo.'}), 400
    
    if not hasattr(user, 'active'):
        return jsonify({'success': False, 'message': 'El campo active no está disponible.'}), 400
    
    user.active = not user.active
    db.session.commit()
    
    status = 'activado' if user.active else 'desactivado'
    return jsonify({
        'success': True, 
        'message': f'Usuario {user.username} ha sido {status} exitosamente.',
        'active': user.active
    })

def generate_reset_token():
    """Genera un token seguro para reset de contraseña"""
    return secrets.token_urlsafe(32)

def send_password_reset_email(user, token):
    """Envía email con enlace para resetear contraseña"""
    from flask import url_for
    reset_url = url_for('main.reset_password', token=token, _external=True)
    
    msg = Message(
        subject='Recuperación de Contraseña - Sistema de Cotizaciones',
        recipients=[user.email],
        sender=current_app.config['MAIL_DEFAULT_SENDER']
    )
    
    msg.body = f"""Hola {user.name or user.username},

Un administrador ha solicitado restablecer tu contraseña en el Sistema de Cotizaciones.

Para restablecer tu contraseña, haz clic en el siguiente enlace:
{reset_url}

Este enlace expirará en 1 hora.

Si no solicitaste este cambio, puedes ignorar este mensaje o contactar al administrador.

Saludos,
Equipo del Sistema de Cotizaciones
"""
    
    msg.html = f"""
    <html>
    <body>
        <h2>Recuperación de Contraseña</h2>
        <p>Hola <strong>{user.name or user.username}</strong>,</p>
        <p>Un administrador ha solicitado restablecer tu contraseña en el Sistema de Cotizaciones.</p>
        <p>Para restablecer tu contraseña, haz clic en el siguiente enlace:</p>
        <p><a href="{reset_url}" style="background-color: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Restablecer Contraseña</a></p>
        <p>O copia y pega este enlace en tu navegador:</p>
        <p>{reset_url}</p>
        <p><strong>Este enlace expirará en 1 hora.</strong></p>
        <p>Si no solicitaste este cambio, puedes ignorar este mensaje o contactar al administrador.</p>
        <hr>
        <p style="color: #666; font-size: 12px;">Saludos,<br>Equipo del Sistema de Cotizaciones</p>
    </body>
    </html>
    """
    
    try:
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Error enviando email de reset: {e}")
        return False

@admin_bp.route('/users/<int:id>/reset_password', methods=['POST'])
@login_required
@role_required(['admin'])
def reset_user_password(id):
    """Permite a un administrador resetear la contraseña de un usuario"""
    user = ensure_company_id(id, User)
    if user.role == 'super_admin':
        flash('No puedes resetear la contraseña del Super Administrador.', 'danger')
        return redirect(url_with_token('admin.list_users'))
    
    # Invalidar tokens anteriores no usados del usuario
    PasswordResetToken.query.filter_by(
        user_id=user.id,
        used=False
    ).update({'used': True})
    db.session.commit()
    
    # Generar nuevo token
    token = generate_reset_token()
    expires_at = datetime.utcnow() + timedelta(hours=1)
    
    # Guardar token en BD
    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=expires_at
    )
    db.session.add(reset_token)
    db.session.commit()
    
    # Enviar email
    if send_password_reset_email(user, token):
        flash(f'Se ha enviado un enlace de recuperación de contraseña al correo de {user.email}.', 'success')
    else:
        flash('Error al enviar el email. Por favor, intenta de nuevo más tarde.', 'danger')
    
    return redirect(url_with_token('admin.list_users'))

@admin_bp.route('/audit_logs')
@login_required
@role_required(['admin'])
def audit_logs():
    """Muestra los logs de auditoría."""
    # Filtros opcionales
    entity_type = request.args.get('entity_type')
    action = request.args.get('action')
    user_id = request.args.get('user_id', type=int)
    
    query = AuditLog.query
    
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    logs = query.order_by(AuditLog.created_at.desc()).limit(500).all()
    
    # Obtener tipos de entidades únicos para el filtro
    entity_types = db.session.query(AuditLog.entity_type).distinct().all()
    entity_types = [et[0] for et in entity_types]
    
    # Obtener acciones únicas para el filtro
    actions = db.session.query(AuditLog.action).distinct().all()
    actions = [a[0] for a in actions]
    
    return render_template(
        'admin/audit_logs.html',
        logs=logs,
        entity_types=entity_types,
        actions=actions,
        title='Logs de Auditoría',
        current_entity_type=entity_type,
        current_action=action,
        current_user_id=user_id
    )

# Rutas para gestión de empresas
@admin_bp.route('/companies')
@login_required
@role_required(['admin', 'super_admin'])
def list_companies():
    """Lista todas las empresas (super-admins ven todas, admins solo la suya)"""
    from app.tenant import is_super_admin
    if is_super_admin():
        base = Company.query
        q = request.args.get('q', '').strip()
        if q:
            base = base.filter(
                or_(
                    Company.name.ilike(f'%{q}%'),
                    Company.legal_name.ilike(f'%{q}%'),
                    Company.tax_id.ilike(f'%{q}%')
                )
            )
        companies = base.order_by(Company.name).all()
    else:
        companies = Company.query.filter_by(id=current_user.company_id).all()
        q = ''
    return render_template(
        'admin/list_companies.html',
        companies=companies,
        title='Empresas',
        filter_q=q,
        filter_show_dates=False,
        filter_show_status=False,
    )

@admin_bp.route('/companies/new', methods=['GET', 'POST'])
@login_required
@super_admin_required
def create_company():
    """Crea una nueva empresa con administrador inicial (solo para super admins)"""
    from app.forms import CreateCompanyWithAdminForm
    form = CreateCompanyWithAdminForm()
    
    if form.validate_on_submit():
        # Crear empresa
        company = Company(
            name=form.name.data,
            legal_name=form.legal_name.data,
            tax_id=form.tax_id.data,
            address=form.address.data,
            phone=form.phone.data,
            email=form.email.data,
            website=form.website.data,
            contact_person=form.contact_person.data or None,
            active=True,
            created_by=current_user.id
        )
        db.session.add(company)
        db.session.flush()  # Para obtener el ID de la empresa
        
        # Crear configuración por defecto
        config = CompanyConfig(
            company_id=company.id,
            default_tax_rate=form.default_tax_rate.data if form.default_tax_rate.data is not None else 0.0,
            monthly_sales_target=form.monthly_sales_target.data if form.monthly_sales_target.data is not None else 10000.0,
            quote_number_prefix=form.quote_number_prefix.data or 'COT',
            invoice_number_prefix=form.invoice_number_prefix.data or 'FAC',
            credit_note_number_prefix=form.credit_note_number_prefix.data or 'NC'
        )
        db.session.add(config)
        
        # Crear administrador inicial (role_id desde tabla roles)
        role_admin = Role.query.filter_by(code='admin').first()
        if not role_admin:
            flash('Rol admin no encontrado en la tabla roles. Ejecute la migración de roles.', 'danger')
            return redirect(url_with_token('admin.create_company_with_admin'))
        admin_user = User(
            name=form.admin_name.data,
            username=form.admin_username.data,
            email=form.admin_email.data,
            company_id=company.id,
            role_id=role_admin.id,
            active=True
        )
        admin_user.set_password(form.admin_password.data)
        db.session.add(admin_user)
        db.session.flush()  # Para obtener el ID del admin
        
        # Asignar created_by a la empresa
        company.created_by = admin_user.id
        
        db.session.commit()
        flash(f'Empresa "{company.name}" y administrador "{admin_user.username}" creados exitosamente.', 'success')
        return redirect(url_with_token('admin.list_companies'))
    
    return render_template('admin/create_company_with_admin.html', form=form, title='Nueva Empresa con Administrador')

@admin_bp.route('/companies/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'super_admin'])
def edit_company(id):
    """Edita una empresa existente (admin: su empresa; super_admin: cualquier empresa)."""
    company = ensure_company_id(id, Company)
    from app.forms import CompanyForm
    form = CompanyForm()
    
    if form.validate_on_submit():
        company.name = form.name.data
        company.legal_name = form.legal_name.data
        company.tax_id = form.tax_id.data
        company.address = form.address.data
        company.phone = form.phone.data
        company.email = form.email.data
        company.website = form.website.data
        company.contact_person = form.contact_person.data or None
        
        # Actualizar configuración (crear si no existe, p. ej. empresa antigua sin config)
        config = CompanyConfig.query.filter_by(company_id=company.id).first()
        if config is None:
            config = CompanyConfig(company_id=company.id)
            db.session.add(config)
            db.session.flush()

        # IVA 0% es válido: leer del request por si el form devuelve None cuando el usuario pone 0
        raw_tax = request.form.get('default_tax_rate')
        if raw_tax is not None and raw_tax != '':
            try:
                tax_val = float(raw_tax)
                config.default_tax_rate = tax_val if 0 <= tax_val <= 100 else 0.0
            except (ValueError, TypeError):
                config.default_tax_rate = form.default_tax_rate.data if form.default_tax_rate.data is not None else 0.0
        else:
            config.default_tax_rate = form.default_tax_rate.data if form.default_tax_rate.data is not None else 0.0

        config.monthly_sales_target = form.monthly_sales_target.data if form.monthly_sales_target.data is not None else 10000.0
        config.quote_number_prefix = form.quote_number_prefix.data or 'COT'
        config.invoice_number_prefix = form.invoice_number_prefix.data or 'FAC'
        config.credit_note_number_prefix = form.credit_note_number_prefix.data or 'NC'

        db.session.commit()
        flash('Empresa actualizada exitosamente.', 'success')
        return redirect(url_with_token('admin.list_companies'))
    elif request.method == 'GET':
        form.name.data = company.name
        form.legal_name.data = company.legal_name
        form.tax_id.data = company.tax_id
        form.address.data = company.address
        form.phone.data = company.phone
        form.email.data = company.email
        form.website.data = company.website
        
        # Cargar configuración (si no hay config, mostrar 0 en IVA para no imponer 19%)
        config = CompanyConfig.query.filter_by(company_id=company.id).first()
        if config:
            form.default_tax_rate.data = config.default_tax_rate if config.default_tax_rate is not None else 0.0
            form.monthly_sales_target.data = config.monthly_sales_target if config.monthly_sales_target is not None else 0.0
            form.quote_number_prefix.data = config.quote_number_prefix or 'COT'
            form.invoice_number_prefix.data = config.invoice_number_prefix or 'FAC'
            form.credit_note_number_prefix.data = config.credit_note_number_prefix or 'NC'
        else:
            form.default_tax_rate.data = 0.0
            form.monthly_sales_target.data = 0.0
            form.quote_number_prefix.data = 'COT'
            form.invoice_number_prefix.data = 'FAC'
            form.credit_note_number_prefix.data = 'NC'
    
    return render_template('admin/create_company.html', form=form, company=company, title='Editar Empresa')

@admin_bp.route('/companies/<int:id>/assign_admin', methods=['GET', 'POST'])
@login_required
@super_admin_required
def assign_admin_to_company(id):
    """Asigna un administrador a una empresa existente"""
    company = Company.query.get_or_404(id)
    from app.forms import AdminCreateUserForm
    from app.tenant import is_super_admin
    
    form = AdminCreateUserForm()
    form.role.choices = get_role_choices_from_db(['admin'])
    form.role.data = 'admin'
    form.role.render_kw = {'disabled': True}  # Deshabilitar campo de rol
    
    if form.validate_on_submit():
        role_admin = Role.query.filter_by(code='admin').first()
        if not role_admin:
            flash('Rol admin no encontrado en la tabla roles. Ejecute la migración de roles.', 'danger')
            return redirect(url_for('admin.assign_admin_to_company', id=company.id))
        # Crear usuario como admin de la empresa
        user = User(
            name=form.name.data,
            username=form.username.data,
            email=form.email.data,
            company_id=company.id,
            role_id=role_admin.id,
            active=True
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        flash(f'Administrador {user.username} asignado a la empresa {company.name} exitosamente.', 'success')
        return redirect(url_with_token('admin.list_companies'))
    
    return render_template('admin/assign_admin.html', form=form, company=company, title=f'Asignar Administrador a {company.name}')


# --- Bodegas (Warehouses) ---
@admin_bp.route('/warehouses')
@login_required
@role_required(['admin', 'super_admin'])
def list_warehouses():
    """Lista bodegas de la empresa del usuario."""
    base_query = filter_by_company(Warehouse.query, Warehouse)
    q = request.args.get('q', '').strip()
    if q:
        base_query = base_query.filter(
            or_(
                Warehouse.name.ilike(f'%{q}%'),
                Warehouse.code.ilike(f'%{q}%')
            )
        )
    status = request.args.get('status', '').strip()
    if status == 'activo':
        base_query = base_query.filter(Warehouse.active == True)
    elif status == 'inactivo':
        base_query = base_query.filter(Warehouse.active == False)
    warehouses = base_query.order_by(Warehouse.name).all()
    return render_template(
        'admin/list_warehouses.html',
        warehouses=warehouses,
        title='Centro de acopio',
        filter_q=q,
        filter_status=status,
        filter_show_dates=False,
        filter_show_status=True,
        filter_status_options=[('', 'Todas'), ('activo', 'Activas'), ('inactivo', 'Inactivas')],
    )


@admin_bp.route('/warehouses/new', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'super_admin'])
def create_warehouse():
    """Crea una nueva sección del centro de acopio. Al crear se agrega ProductWarehouseStock (0) para todos los productos."""
    form = WarehouseForm()
    if form.validate_on_submit():
        company_id = get_current_company_id()
        if not company_id:
            flash('No tiene empresa asignada. Solo administradores de empresa pueden crear bodegas.', 'danger')
            return redirect(url_with_token('admin.list_warehouses'))
        code = (form.code.data or '').strip() or _code_from_warehouse_name(form.name.data or '')
        warehouse = Warehouse(
            company_id=company_id,
            name=form.name.data,
            code=code or None,
            address=form.address.data or None,
            warehouse_type=form.warehouse_type.data,
            active=form.active.data
        )
        db.session.add(warehouse)
        db.session.flush()
        for product in Product.query.filter_by(company_id=company_id).all():
            pws = ProductWarehouseStock(product_id=product.id, warehouse_id=warehouse.id, quantity=0)
            db.session.add(pws)
        db.session.commit()
        flash(f'Sección "{warehouse.name}" creada correctamente.', 'success')
        return redirect(url_with_token('admin.list_warehouses'))
    return render_template('admin/form_warehouse.html', form=form, warehouse=None, title='Nueva sección')


def _code_from_warehouse_name(name):
    """Genera un código corto a partir del nombre de la sección (ej. BODEGA PRINCIPAL -> BOD-PRI)."""
    if not name or not name.strip():
        return ''
    import re
    s = name.strip().upper()
    for c, r in (('Á', 'A'), ('É', 'E'), ('Í', 'I'), ('Ó', 'O'), ('Ú', 'U'), ('Ñ', 'N')):
        s = s.replace(c, r)
    words = [w for w in re.split(r'\s+', s) if len(w) >= 2]
    stop = ('DE', 'LA', 'EL', 'EN', 'Y', 'DEL', 'LOS', 'LAS')
    words = [w for w in words if w not in stop]
    if not words:
        return s[:8].replace(' ', '-') if s else ''
    parts = []
    for w in words[:3]:
        parts.append(w[:3] if len(w) >= 3 else w)
    return '-'.join(parts)[:20]


def _warehouse_type_for_form(warehouse_type):
    """Convierte tipos legacy (mayorista/minorista) a los dos tipos del formulario (general/farmacia)."""
    if warehouse_type == 'mayorista':
        return 'general'
    if warehouse_type == 'minorista':
        return 'farmacia'
    return warehouse_type if warehouse_type in ('general', 'farmacia') else 'general'


@admin_bp.route('/warehouses/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'super_admin'])
def edit_warehouse(id):
    """Edita una sección del centro de acopio. El campo Sección solo ofrece: Almacén General y Farmacia."""
    warehouse = ensure_company_id(id, Warehouse)
    form = WarehouseForm()
    # Siempre solo dos opciones, sin duplicados
    form.warehouse_type.choices = list(WAREHOUSE_SECTION_TYPES)
    if form.validate_on_submit():
        warehouse.name = form.name.data
        warehouse.code = form.code.data or None
        warehouse.address = form.address.data or None
        warehouse.warehouse_type = form.warehouse_type.data
        warehouse.active = form.active.data
        db.session.commit()
        flash('Sección actualizada correctamente.', 'success')
        return redirect(url_with_token('admin.list_warehouses'))
    if request.method == 'GET':
        form.name.data = warehouse.name
        form.code.data = warehouse.code
        form.address.data = warehouse.address
        form.warehouse_type.data = _warehouse_type_for_form(warehouse.warehouse_type)
        form.active.data = warehouse.active
    return render_template('admin/form_warehouse.html', form=form, warehouse=warehouse, title='Editar sección')


# --- Almacenes de entrega (Delivery Points) ---
@admin_bp.route('/delivery-points')
@login_required
@role_required(['admin', 'super_admin'])
def list_delivery_points():
    """Lista almacenes de entrega de la empresa."""
    from sqlalchemy import or_
    base_query = filter_by_company(DeliveryPoint.query, DeliveryPoint)
    q = request.args.get('q', '').strip()
    if q:
        base_query = base_query.filter(
            or_(
                DeliveryPoint.name.ilike(f'%{q}%'),
                DeliveryPoint.code.ilike(f'%{q}%')
            )
        )
    status = request.args.get('status', '').strip()
    if status == 'activo':
        base_query = base_query.filter(DeliveryPoint.active == True)
    elif status == 'inactivo':
        base_query = base_query.filter(DeliveryPoint.active == False)
    delivery_points = base_query.order_by(DeliveryPoint.name).all()
    return render_template(
        'admin/list_delivery_points.html',
        delivery_points=delivery_points,
        title='Puntos de despacho',
        filter_q=q,
        filter_status=status,
        filter_show_status=True,
        filter_status_options=[('', 'Todos'), ('activo', 'Activo'), ('inactivo', 'Inactivo')],
    )


def _next_delivery_point_code(company_id):
    """Genera el siguiente código para almacén de entrega: ENT-01, ENT-02, ..."""
    import re
    existing = DeliveryPoint.query.filter_by(company_id=company_id).all()
    max_num = 0
    for dp in existing:
        if dp.code and re.match(r'^ENT-(\d+)$', (dp.code or '').strip(), re.IGNORECASE):
            max_num = max(max_num, int(re.match(r'^ENT-(\d+)$', dp.code.strip(), re.IGNORECASE).group(1)))
    return f'ENT-{max_num + 1:02d}'


@admin_bp.route('/delivery-points/new', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'super_admin'])
def create_delivery_point():
    """Crea un nuevo punto de despacho."""
    from app.forms import DeliveryPointForm
    form = DeliveryPointForm()
    company_id = get_current_company_id()
    warehouses = Warehouse.query.filter_by(company_id=company_id, active=True).order_by(Warehouse.name).all() if company_id else []
    form.warehouse_id.choices = [('', '-- Ninguna --')] + [(w.id, f'{w.name} ({WAREHOUSE_TYPE_LABELS.get(w.warehouse_type, w.warehouse_type)})') for w in warehouses]
    if form.validate_on_submit():
        if not company_id:
            flash('No tiene empresa asignada.', 'danger')
            return redirect(url_with_token('admin.list_delivery_points'))
        code = (form.code.data or '').strip() or _next_delivery_point_code(company_id)
        dp = DeliveryPoint(
            company_id=company_id,
            name=form.name.data,
            code=code,
            address=form.address.data or None,
            active=form.active.data,
            warehouse_id=form.warehouse_id.data or None
        )
        db.session.add(dp)
        db.session.commit()
        flash(f'Punto de despacho "{dp.name}" creado correctamente.', 'success')
        return redirect(url_with_token('admin.list_delivery_points'))
    return render_template('admin/form_delivery_point.html', form=form, delivery_point=None, title='Nuevo punto de despacho')


@admin_bp.route('/delivery-points/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'super_admin'])
def edit_delivery_point(id):
    """Edita un punto de despacho."""
    from app.forms import DeliveryPointForm
    dp = ensure_company_id(id, DeliveryPoint)
    form = DeliveryPointForm()
    warehouses = Warehouse.query.filter_by(company_id=dp.company_id, active=True).order_by(Warehouse.name).all()
    form.warehouse_id.choices = [('', '-- Ninguna --')] + [(w.id, f'{w.name} ({WAREHOUSE_TYPE_LABELS.get(w.warehouse_type, w.warehouse_type)})') for w in warehouses]
    if form.validate_on_submit():
        dp.name = form.name.data
        dp.code = (form.code.data or '').strip() or _next_delivery_point_code(dp.company_id)
        dp.address = form.address.data or None
        dp.warehouse_id = form.warehouse_id.data or None
        dp.active = form.active.data
        db.session.commit()
        flash('Punto de despacho actualizado correctamente.', 'success')
        return redirect(url_with_token('admin.list_delivery_points'))
    if request.method == 'GET':
        form.name.data = dp.name
        form.code.data = dp.code
        form.address.data = dp.address
        form.warehouse_id.data = dp.warehouse_id
        form.active.data = dp.active
    return render_template('admin/form_delivery_point.html', form=form, delivery_point=dp, title='Editar punto de despacho')


@admin_bp.route('/users/all')
@login_required
@super_admin_required
def list_all_users():
    """Lista todos los usuarios de todas las empresas (solo para super-admins). Token validado por before_request."""
    token = request.args.get('token') or ''
    query = (request.args.get('q') or '').strip()
    show_inactive = request.args.get('show_inactive', 'false') == 'true' or request.args.get('status', '').strip() == 'inactivos'
    base_query = User.query
    if not show_inactive:
        base_query = base_query.filter(User.active == True)
    if query:
        users = base_query.filter(
            or_(
                User.username.ilike(f'%{query}%'),
                User.name.ilike(f'%{query}%'),
                User.email.ilike(f'%{query}%')
            )
        ).order_by(User.company_id, User.username).all()
    else:
        users = base_query.order_by(User.company_id, User.username).all()
    return render_template(
        'admin/list_all_users.html',
        users=users,
        title='Todos los Usuarios',
        q=query,
        show_inactive=show_inactive,
        admin_route_token=token,
        filter_q=query,
        filter_show_dates=False,
        filter_show_status=True,
        filter_status='inactivos' if show_inactive else '',
        filter_status_options=[('', 'Solo activos'), ('inactivos', 'Incluir inactivos')],
    )

@admin_bp.route('/users/<int:user_id>/assign_company', methods=['GET', 'POST'])
@login_required
@super_admin_required
def assign_user_to_company(user_id):
    """Asigna un usuario a una empresa (solo super-admins). No aplica a usuarios con rol super_admin."""
    user = User.query.get_or_404(user_id)
    from app.models import Company
    from app.route_tokens import url_with_token

    if user.role == 'super_admin':
        flash('Los Administradores generales (super admin) no se asignan a empresas; son ellos quienes las asignan.', 'info')
        return redirect(url_with_token('admin.list_all_users'))

    if request.method == 'POST':
        company_id = request.form.get('company_id', type=int)
        if company_id:
            company = Company.query.get_or_404(company_id)
            user.company_id = company_id
            db.session.commit()
            flash(f'Usuario {user.username} asignado a la empresa {company.name} exitosamente.', 'success')
            return redirect(url_with_token('admin.list_all_users'))

    companies = Company.query.order_by(Company.name).all()
    return render_template('admin/assign_user_to_company.html', user=user, companies=companies, title='Asignar Usuario a Empresa')
