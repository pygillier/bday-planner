import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db as _db
from app.models import Guest


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def guest(app):
    g = Guest(first_name="Jeanne", last_name="Dupont", email="jeanne@example.com")
    _db.session.add(g)
    _db.session.commit()
    return g
