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
            assert exc_info.value.code == 404
