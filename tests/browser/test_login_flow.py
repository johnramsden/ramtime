import pytest
from pathlib import Path

SCREENSHOTS = Path(__file__).parent / "screenshots"


def test_login_page_renders(page, live_server):
    page.goto(f"{live_server}/login")
    assert page.title() == "Login — Ramtime"
    assert page.locator("h1").inner_text() == "Sign in"
    page.screenshot(path=SCREENSHOTS / "login_page.png")


def test_successful_employee_login_redirects_to_dashboard(page, live_server):
    page.goto(f"{live_server}/login")
    page.fill("#username", "testemployee")
    page.fill("#password", "emppass")
    page.screenshot(path=SCREENSHOTS / "login_filled.png")
    page.click("button[type=submit]")
    page.wait_for_url(f"{live_server}/employee/")
    assert "/employee/" in page.url
    page.screenshot(path=SCREENSHOTS / "employee_dashboard_after_login.png")


def test_successful_admin_login_redirects_to_admin_dashboard(page, live_server):
    page.goto(f"{live_server}/login")
    page.fill("#username", "testadmin")
    page.fill("#password", "adminpass")
    page.click("button[type=submit]")
    page.wait_for_url(f"{live_server}/admin/")
    assert "/admin/" in page.url
    page.screenshot(path=SCREENSHOTS / "admin_dashboard_after_login.png")


def test_failed_login_shows_error(page, live_server):
    page.goto(f"{live_server}/login")
    page.fill("#username", "testemployee")
    page.fill("#password", "wrongpassword")
    page.click("button[type=submit]")
    # Stay on login page
    assert "/login" in page.url
    assert "Invalid" in page.locator(".alert").inner_text()
    page.screenshot(path=SCREENSHOTS / "login_error.png")


def test_logout_redirects_to_login(employee_page, live_server):
    employee_page.locator("button:has-text('Logout')").click()
    employee_page.wait_for_url(f"{live_server}/login")
    assert "Sign in" in employee_page.locator("h1").inner_text()
    employee_page.screenshot(path=SCREENSHOTS / "after_logout.png")
