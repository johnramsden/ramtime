import pytest
from datetime import datetime

from app import create_app
from app.extensions import db as _db
from app.models import User, TimeEntry, Setting


@pytest.fixture(scope="session")
def app():
    application = create_app("testing")
    return application


@pytest.fixture()
def db(app):
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(db, app):
    return app.test_client()


@pytest.fixture()
def employee_user(db):
    from app.extensions import bcrypt
    user = User(
        name="Alice Employee",
        username="alice",
        password_hash=bcrypt.generate_password_hash("password").decode(),
        role="employee",
    )
    _db.session.add(user)
    _db.session.commit()
    return user


@pytest.fixture()
def admin_user(db):
    from app.extensions import bcrypt
    user = User(
        name="Bob Admin",
        username="bobadmin",
        password_hash=bcrypt.generate_password_hash("adminpass").decode(),
        role="admin",
    )
    _db.session.add(user)
    _db.session.commit()
    return user


@pytest.fixture()
def employee_client(app, db, employee_user):
    """Fresh test client logged in as an employee."""
    c = app.test_client()
    c.post("/login", data={"username": "alice", "password": "password"})
    return c


@pytest.fixture()
def admin_client(app, db, admin_user):
    """Fresh test client logged in as admin."""
    c = app.test_client()
    c.post("/login", data={"username": "bobadmin", "password": "adminpass"})
    return c


@pytest.fixture()
def default_setting(db):
    s = Setting(key="default_minimum_hours", value="3.0")
    _db.session.add(s)
    _db.session.commit()
    return s


def make_entry(user_id, start, end=None, note=None, minimum_hours=None):
    """Helper to create and persist a TimeEntry."""
    entry = TimeEntry(
        user_id=user_id,
        start_time=start,
        end_time=end,
        note=note,
        minimum_hours=minimum_hours,
    )
    _db.session.add(entry)
    _db.session.commit()
    return entry
