import datetime
import pytest
from flask_login import login_user
from werkzeug.exceptions import HTTPException


def test_ensure_company_id_blocks_cross_tenant_quote(app):
    from app import db
    from app.models import Company, User, Role, Client, Product, Quote
    from app.tenant import ensure_company_id

    with app.app_context():
        role = Role(code='admin', label='Administrador')
        db.session.add(role)
        db.session.flush()

        c1 = Company(name='Empresa 1', active=True)
        c2 = Company(name='Empresa 2', active=True)
        db.session.add_all([c1, c2])
        db.session.flush()

        u1 = User(
            username='admin1',
            email='a1@test.com',
            company_id=c1.id,
            role_id=role.id,
            active=True,
        )
        u1.set_password('pass123')
        db.session.add(u1)

        cl2 = Client(company_id=c2.id, name='Cliente 2', email='c2@test.com')
        db.session.add(cl2)
        db.session.flush()

        quote = Quote(
            company_id=c2.id,
            quote_number='COT-001',
            date=datetime.datetime.utcnow(),
            client_id=cl2.id,
            total_amount=10.0,
        )
        db.session.add(quote)
        db.session.commit()
        quote_id = quote.id

        with app.test_request_context():
            login_user(u1)
            with pytest.raises(HTTPException) as exc_info:
                ensure_company_id(quote_id, Quote)
            assert exc_info.value.code == 403


def test_resolve_entity_company_id_from_client(app):
    from app import db
    from app.models import Company, Client, Quote
    from app.tenant import resolve_entity_company_id

    with app.app_context():
        company = Company(name='Empresa Cliente', active=True)
        db.session.add(company)
        db.session.flush()
        client = Client(company_id=company.id, name='Cliente', email='c@test.com')
        quote = Quote(
            quote_number='LEG-001',
            date=datetime.datetime.utcnow(),
            client_id=client.id,
            total_amount=10.0,
        )
        quote.company_id = None
        quote.client = client

        assert resolve_entity_company_id(quote) == company.id
