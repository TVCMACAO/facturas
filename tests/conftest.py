import os
import pytest


@pytest.fixture
def app():
    os.environ['SECRET_KEY'] = 'test-secret-key-for-pytest-only'
    os.environ['DATABASE_URL'] = 'sqlite://'
    os.environ.pop('FLASK_ENV', None)

    from app import create_app, db

    application = create_app()
    application.config['TESTING'] = True
    application.config['WTF_CSRF_ENABLED'] = False

    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
