from pathlib import Path

SCREENSHOTS = Path(__file__).parent / "screenshots"


def _fill_time(page, start_h, start_m, end_h, end_m):
    page.select_option("select[name='start_hour']", start_h)
    page.select_option("select[name='start_minute']", start_m)
    page.select_option("select[name='end_hour']", end_h)
    page.select_option("select[name='end_minute']", end_m)


def _current_month():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m")


def _today():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")


def test_manual_entry_form_renders(employee_page, live_server):
    employee_page.goto(f"{live_server}/employee/entry/new")
    assert "Add Entry" in employee_page.title()
    assert employee_page.locator("#date").count() == 1
    assert employee_page.locator("select[name='start_hour']").count() == 1
    assert employee_page.locator("select[name='end_hour']").count() == 1
    employee_page.screenshot(path=SCREENSHOTS / "manual_entry_form.png")


def test_submit_valid_entry_appears_in_log(employee_page, live_server):
    month = _current_month()
    today = _today()
    employee_page.goto(f"{live_server}/employee/entry/new")
    employee_page.fill("#date", today)
    _fill_time(employee_page, "08", "00", "09", "00")
    employee_page.fill("#note", "Browser test entry")
    employee_page.screenshot(path=SCREENSHOTS / "manual_entry_filled.png")
    employee_page.click("button[type=submit]")
    employee_page.wait_for_url(f"{live_server}/employee/log")
    employee_page.goto(f"{live_server}/employee/log?month={month}")
    assert "Browser test entry" in employee_page.content()
    employee_page.screenshot(path=SCREENSHOTS / "manual_entry_in_log.png")


def test_manual_entry_shows_billed_hours(employee_page, live_server):
    # 1h actual, global minimum 3h → billed should show 3.00
    month = _current_month()
    today = _today()
    employee_page.goto(f"{live_server}/employee/entry/new")
    employee_page.fill("#date", today)
    _fill_time(employee_page, "08", "00", "09", "00")
    employee_page.click("button[type=submit]")
    employee_page.wait_for_url(f"{live_server}/employee/log")
    employee_page.goto(f"{live_server}/employee/log?month={month}")
    assert "3.00" in employee_page.content()
    employee_page.screenshot(path=SCREENSHOTS / "billed_hours_minimum.png")


def test_manual_entry_note_persisted(employee_page, live_server):
    month = _current_month()
    today = _today()
    employee_page.goto(f"{live_server}/employee/entry/new")
    employee_page.fill("#date", today)
    _fill_time(employee_page, "08", "00", "09", "00")
    employee_page.fill("#note", "Persistent note test")
    employee_page.click("button[type=submit]")
    employee_page.wait_for_url(f"{live_server}/employee/log")
    employee_page.goto(f"{live_server}/employee/log?month={month}")
    assert "Persistent note test" in employee_page.content()
    employee_page.screenshot(path=SCREENSHOTS / "note_in_log.png")
