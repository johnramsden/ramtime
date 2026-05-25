import threading
import time
import pytest

from app import create_app
from app.extensions import db as _db, bcrypt
from app.models import User, Setting


@pytest.fixture(scope="session")
def live_app():
    """Create a Flask app configured for browser testing."""
    application = create_app("testing")
    # Override server name so url_for works without a request context
    application.config["SERVER_NAME"] = None
    return application


@pytest.fixture(scope="session")
def live_server(live_app):
    """Start Flask dev server in a background thread for Playwright tests."""
    with live_app.app_context():
        _db.create_all()

        # Seed an admin and employee user
        pw_admin = bcrypt.generate_password_hash("adminpass").decode()
        pw_emp = bcrypt.generate_password_hash("emppass").decode()

        admin = User(name="Test Admin", username="testadmin",
                     password_hash=pw_admin, role="admin")
        emp = User(name="Test Employee", username="testemployee",
                   password_hash=pw_emp, role="employee")
        _db.session.add_all([admin, emp])

        setting = Setting(key="default_minimum_hours", value="3.0")
        _db.session.add(setting)
        _db.session.commit()

    server_thread = threading.Thread(
        target=lambda: live_app.run(host="127.0.0.1", port=5099, use_reloader=False),
        daemon=True,
    )
    server_thread.start()
    time.sleep(1)  # Allow server to start

    yield "http://127.0.0.1:5099"

    with live_app.app_context():
        _db.drop_all()


@pytest.fixture()
def page(browser):
    """Fresh Playwright page for each test."""
    ctx = browser.new_context()
    p = ctx.new_page()
    yield p
    p.close()
    ctx.close()


@pytest.fixture()
def employee_page(page, live_server):
    """Page already logged in as employee with no active entry."""
    page.goto(f"{live_server}/login")
    page.fill("#username", "testemployee")
    page.fill("#password", "emppass")
    page.click("button[type=submit]")
    page.wait_for_url(f"{live_server}/employee/")
    # Ensure no dangling active entry from previous tests
    if page.locator("#active-entry-card").count() > 0:
        page.locator("button:has-text('Stop')").first.click()
        page.wait_for_selector("#active-entry-card", state="detached")
    return page


@pytest.fixture()
def admin_page(page, live_server):
    """Page already logged in as admin."""
    page.goto(f"{live_server}/login")
    page.fill("#username", "testadmin")
    page.fill("#password", "adminpass")
    page.click("button[type=submit]")
    page.wait_for_url(f"{live_server}/admin/")
    return page
