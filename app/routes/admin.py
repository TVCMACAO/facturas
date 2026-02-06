from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_
from app import db, mail
from app.models import User, AuditLog, PasswordResetToken
from app.decorators import role_required
from app.forms import AdminEditUserForm
from flask_mail import Message
from datetime import datetime, timedelta
import secrets

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/users')
@login_required
@role_required(['admin'])
def list_users():
    query = request.args.get('q')
    if query:
        users = User.query.filter(
            or_(
                User.username.ilike(f'%{query}%'),
                User.name.ilike(f'%{query}%'),
                User.email.ilike(f'%{query}%')
            )
        ).order_by(User.username).all()
    else:
        users = User.query.order_by(User.username).all()
    
    return render_template('admin/list_users.html', users=users, title='Administración de Usuarios', q=query)

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
    user = User.query.get_or_404(id)
    form = AdminEditUserForm(original_username=user.username, original_email=user.email)
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.role = form.role.data
        db.session.commit()
        flash('El usuario ha sido actualizado exitosamente.', 'success')
        return redirect(url_for('admin.list_users'))
    elif request.method == 'GET':
        form.username.data = user.username
        form.email.data = user.email
        form.role.data = user.role
    return render_template('admin/edit_user.html', form=form, user=user, title="Editar Usuario")

@admin_bp.route('/users/<int:id>/delete', methods=['POST'])
@login_required
@role_required(['admin'])
def delete_user(id):
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        flash('No puedes eliminarte a ti mismo.', 'danger')
        return redirect(url_for('admin.list_users'))
    
    # Reassign any items owned by the user if necessary, or handle otherwise
    # For now, we'll just delete the user
    db.session.delete(user)
    db.session.commit()
    flash(f'Usuario {user.username} eliminado exitosamente.', 'success')
    return redirect(url_for('admin.list_users'))

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
    user = User.query.get_or_404(id)
    
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
    
    return redirect(url_for('admin.list_users'))

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
