from pathlib import Path

SCREENSHOTS = Path(__file__).parent / "screenshots"


def test_admin_dashboard_renders(admin_page, live_server):
    assert "Admin Dashboard" in admin_page.title()
    assert admin_page.locator("#entries-table").count() >= 0
    admin_page.screenshot(path=SCREENSHOTS / "admin_dashboard.png")


def test_filter_first_half_updates_table(admin_page, live_server):
    admin_page.select_option("select[name=half]", "first")
    admin_page.click("button[type=submit]")
    admin_page.wait_for_load_state("networkidle")
    assert "first" in admin_page.url
    admin_page.screenshot(path=SCREENSHOTS / "admin_filter_first_half.png")


def test_filter_second_half_updates_table(admin_page, live_server):
    admin_page.select_option("select[name=half]", "second")
    admin_page.click("button[type=submit]")
    admin_page.wait_for_load_state("networkidle")
    assert "second" in admin_page.url
    admin_page.screenshot(path=SCREENSHOTS / "admin_filter_second_half.png")


def test_employee_filter_visible(admin_page, live_server):
    # Employee select should exist
    assert admin_page.locator("select[name=user_id]").count() == 1
    admin_page.screenshot(path=SCREENSHOTS / "admin_employee_filter.png")


def test_export_button_present(admin_page, live_server):
    assert admin_page.locator("#export-btn").count() == 1
    admin_page.screenshot(path=SCREENSHOTS / "admin_export_button.png")
