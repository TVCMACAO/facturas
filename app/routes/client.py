from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Client, Invoice, Payment
from app.forms import ClientForm
from app.tenant import filter_by_company, ensure_company_id
from app.decorators import role_required, log_audit
from sqlalchemy import or_

clients_bp = Blueprint('clients', __name__, url_prefix='/clients')

@clients_bp.route('/')
@login_required
def list_clients():
    q = request.args.get('q')
    base_query = filter_by_company(Client.query, Client)
    if q:
        clients = base_query.filter(
            or_(
                Client.name.ilike(f'%{q}%'),
                Client.email.ilike(f'%{q}%'),
                Client.document_number.ilike(f'%{q}%')
            )
        ).all()
    else:
        clients = base_query.all()
    q = (q or '').strip()
    return render_template(
        'clients/list.html',
        clients=clients,
        title='Clientes',
        q=q,
        filter_q=q,
        filter_show_dates=False,
        filter_show_status=False,
    )

@clients_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required(['user', 'admin', 'super_admin'])
def add_client():
    form = ClientForm()
    if form.validate_on_submit():
        client = Client(
            name=form.name.data,
            document_number=form.document_number.data,
            contact_person=form.contact_person.data,
            email=form.email.data,
            phone=form.phone.data,
            whatsapp_number=form.whatsapp_number.data,
            address=form.address.data,
            company_id=current_user.company_id
        )
        db.session.add(client)
        db.session.commit()
        flash('Cliente añadido con éxito.', 'success')
        return redirect(url_for('clients.list_clients'))
    return render_template('clients/form.html', form=form, title='Añadir Cliente')

@clients_bp.route('/<string:invalid_id>')
@login_required
def invalid_client_id(invalid_id):
    """Maneja IDs inválidos (strings) y devuelve 404 después de verificar autenticación"""
    from flask import abort
    abort(404)

@clients_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required(['user', 'admin', 'super_admin'])
def edit_client(id):
    client = ensure_company_id(id, Client)
    form = ClientForm(obj=client)
    form.instance = client # Pass instance to form for validation
    if form.validate_on_submit():
        client.name = form.name.data
        client.document_number = form.document_number.data
        client.contact_person = form.contact_person.data
        client.email = form.email.data
        client.phone = form.phone.data
        client.whatsapp_number = form.whatsapp_number.data
        client.address = form.address.data
        db.session.commit()
        flash('Cliente actualizado con éxito.', 'success')
        return redirect(url_for('clients.list_clients'))
    return render_template('clients/form.html', form=form, title='Editar Cliente')

@clients_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@role_required(['user', 'admin', 'super_admin'])
def delete_client(id):
    client = ensure_company_id(id, Client)
    client_id = client.id
    db.session.delete(client)
    db.session.commit()
    log_audit('delete', 'client', client_id)
    flash('Cliente eliminado con éxito.', 'success')
    return redirect(url_for('clients.list_clients'))

@clients_bp.route('/<int:id>/payments')
@login_required
def view_client_payments(id):
    client = ensure_company_id(id, Client)
    # Fetch all invoices for this client (ya filtradas por company_id a través de la relación)
    invoices = client.invoices.all()
    
    # Collect all payments from these invoices
    all_payments = []
    for invoice in invoices:
        all_payments.extend(invoice.payments) # Fetch all payments for each invoice
    
    # Sort payments by date (optional, but good for display)
    all_payments.sort(key=lambda p: p.payment_date, reverse=True)

    return render_template('clients/payments.html', client=client, payments=all_payments, title=f'Pagos de {client.name}')