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
