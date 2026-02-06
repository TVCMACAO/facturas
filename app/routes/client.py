from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app import db
from app.models import Client, Invoice, Payment
from app.forms import ClientForm
from sqlalchemy import or_

clients_bp = Blueprint('clients', __name__, url_prefix='/clients')

@clients_bp.route('/')
@login_required
def list_clients():
    q = request.args.get('q')
    if q:
        clients = Client.query.filter(
            or_(
                Client.name.ilike(f'%{q}%'),
                Client.email.ilike(f'%{q}%'),
                Client.document_number.ilike(f'%{q}%')
            )
        ).all()
    else:
        clients = Client.query.all()
    return render_template('clients/list.html', clients=clients, title='Clientes', q=q)

@clients_bp.route('/new', methods=['GET', 'POST'])
@login_required
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
            address=form.address.data
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
def edit_client(id):
    client = Client.query.get_or_404(id)
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
def delete_client(id):
    client = Client.query.get_or_404(id)
    db.session.delete(client)
    db.session.commit()
    flash('Cliente eliminado con éxito.', 'success')
    return redirect(url_for('clients.list_clients'))

@clients_bp.route('/<int:id>/payments')
@login_required
def view_client_payments(id):
    client = Client.query.get_or_404(id)
    # Fetch all invoices for this client
    invoices = client.invoices.all()
    
    # Collect all payments from these invoices
    all_payments = []
    for invoice in invoices:
        all_payments.extend(invoice.payments) # Fetch all payments for each invoice
    
    # Sort payments by date (optional, but good for display)
    all_payments.sort(key=lambda p: p.payment_date, reverse=True)

    return render_template('clients/payments.html', client=client, payments=all_payments, title=f'Pagos de {client.name}')