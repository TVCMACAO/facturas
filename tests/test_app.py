import os
import datetime
import pytest
from importlib import reload


def test_health_endpoint(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.get_json()['status'] == 'ok'


def test_production_config_requires_secret_key(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.delenv('SECRET_KEY', raising=False)

    import config
    reload(config)

    is_valid, errors = config.ProductionConfig.validate_config()
    assert not is_valid
    assert any('SECRET_KEY' in e for e in errors)


def test_next_invoice_number_per_company(app):
    from app import db
    from app.models import Company, Client, Invoice
    from app.numbering import next_invoice_number

    with app.app_context():
        c1 = Company(name='Empresa A', active=True)
        c2 = Company(name='Empresa B', active=True)
        db.session.add_all([c1, c2])
        db.session.flush()

        cl1 = Client(company_id=c1.id, name='Cliente A', email='a@test.com')
        cl2 = Client(company_id=c2.id, name='Cliente B', email='b@test.com')
        db.session.add_all([cl1, cl2])
        db.session.flush()

        inv1 = Invoice(
            company_id=c1.id,
            client_id=cl1.id,
            invoice_number='0120',
            date=datetime.datetime.utcnow(),
            total_amount=100.0,
        )
        inv2 = Invoice(
            company_id=c2.id,
            client_id=cl2.id,
            invoice_number='0120',
            date=datetime.datetime.utcnow(),
            total_amount=50.0,
        )
        db.session.add_all([inv1, inv2])
        db.session.commit()

        assert next_invoice_number(c1.id) == '0121'
        assert next_invoice_number(c2.id) == '0121'


def test_next_invoice_number_starts_at_118(app):
    from app import db
    from app.models import Company
    from app.numbering import next_invoice_number

    with app.app_context():
        company = Company(name='Nueva', active=True)
        db.session.add(company)
        db.session.commit()
        assert next_invoice_number(company.id) == '0118'


def test_next_invoice_number_ignores_null_and_non_numeric(app):
    from app import db
    from app.models import Company, Client, Invoice
    from app.numbering import next_invoice_number

    with app.app_context():
        company = Company(name='Empresa C', active=True)
        db.session.add(company)
        db.session.flush()
        client = Client(company_id=company.id, name='Cliente C', email='c@test.com')
        db.session.add(client)
        db.session.flush()

        inv1 = Invoice(
            company_id=company.id,
            client_id=client.id,
            invoice_number='0125',
            date=datetime.datetime.utcnow(),
            total_amount=100.0,
        )
        inv2 = Invoice(
            company_id=company.id,
            client_id=client.id,
            invoice_number='FAC-0126',
            date=datetime.datetime.utcnow(),
            total_amount=50.0,
        )
        db.session.add_all([inv1, inv2])
        db.session.commit()

        assert next_invoice_number(company.id) == '0126'


def test_convert_to_invoice_creates_invoice(app, client):
    from app import db
    from app.models import Company, User, Role, Client, Product, Quote, QuoteItem, Invoice
    from app.routes.quote import generate_view_token

    with app.app_context():
        role = Role(code='admin', label='Administrador')
        db.session.add(role)
        db.session.flush()

        company = Company(name='Empresa Conv', active=True)
        db.session.add(company)
        db.session.flush()

        user = User(
            username='admin_conv',
            email='conv@test.com',
            company_id=company.id,
            role_id=role.id,
            active=True,
        )
        user.set_password('pass123')
        db.session.add(user)

        cl = Client(company_id=company.id, name='Cliente Conv', email='cl@test.com')
        product = Product(
            company_id=company.id,
            code='P001',
            name='Producto Test',
            price=100.0,
            stock=10,
        )
        db.session.add_all([cl, product])
        db.session.flush()

        quote = Quote(
            company_id=company.id,
            quote_number='0100',
            date=datetime.datetime.utcnow(),
            client_id=cl.id,
            subtotal=200.0,
            total_amount=200.0,
            status='pendiente',
        )
        db.session.add(quote)
        db.session.flush()
        db.session.add(QuoteItem(
            quote_id=quote.id,
            product_id=product.id,
            quantity=2,
            unit_price=100.0,
            total_price=200.0,
        ))
        db.session.commit()

        quote_id = quote.id
        token = generate_view_token(quote_id, 'quote')

    client.post('/', data={'username': 'admin_conv', 'password': 'pass123'}, follow_redirects=True)
    response = client.post(
        f'/quotes/{quote_id}/{token}/convert_to_invoice',
        follow_redirects=False,
    )

    assert response.status_code in (302, 303)

    with app.app_context():
        invoice = Invoice.query.filter_by(quote_id=quote_id).first()
        assert invoice is not None
        assert invoice.invoice_number == '0118'
        assert invoice.items.count() == 1


def test_convert_to_invoice_works_with_get(app, client):
    """Enlaces GET antiguos (<a href>) deben seguir convirtiendo la cotización."""
    from app import db
    from app.models import Company, User, Role, Client, Product, Quote, QuoteItem, Invoice
    from app.routes.quote import generate_view_token

    with app.app_context():
        role = Role(code='admin', label='Administrador')
        db.session.add(role)
        db.session.flush()

        company = Company(name='Empresa GET', active=True)
        db.session.add(company)
        db.session.flush()

        user = User(
            username='admin_get',
            email='get@test.com',
            company_id=company.id,
            role_id=role.id,
            active=True,
        )
        user.set_password('pass123')
        db.session.add(user)

        cl = Client(company_id=company.id, name='Cliente GET', email='getcl@test.com')
        product = Product(
            company_id=company.id,
            code='P002',
            name='Producto GET',
            price=50.0,
            stock=5,
        )
        db.session.add_all([cl, product])
        db.session.flush()

        quote = Quote(
            company_id=company.id,
            quote_number='0200',
            date=datetime.datetime.utcnow(),
            client_id=cl.id,
            subtotal=100.0,
            total_amount=100.0,
            status='pendiente',
        )
        db.session.add(quote)
        db.session.flush()
        db.session.add(QuoteItem(
            quote_id=quote.id,
            product_id=product.id,
            quantity=2,
            unit_price=50.0,
            total_price=100.0,
        ))
        db.session.commit()

        quote_id = quote.id
        token = generate_view_token(quote_id, 'quote')

    client.post('/', data={'username': 'admin_get', 'password': 'pass123'}, follow_redirects=True)
    response = client.get(
        f'/quotes/{quote_id}/{token}/convert_to_invoice',
        follow_redirects=False,
    )

    assert response.status_code in (302, 303)

    with app.app_context():
        invoice = Invoice.query.filter_by(quote_id=quote_id).first()
        assert invoice is not None
        assert invoice.invoice_number == '0118'
