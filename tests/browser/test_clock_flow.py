from pathlib import Path

SCREENSHOTS = Path(__file__).parent / "screenshots"


def test_clock_in_button_visible_when_not_active(employee_page, live_server):
    # Ensure no active entry card
    assert employee_page.locator("#active-entry-card").count() == 0
    assert employee_page.locator("button", has_text="Clock in").count() == 1
    employee_page.screenshot(path=SCREENSHOTS / "clock_not_active.png")


def test_clock_in_shows_active_entry_card(employee_page, live_server):
    employee_page.click("button[type=submit]")  # Clock in button
    employee_page.wait_for_selector("#active-entry-card")
    assert employee_page.locator("#active-entry-card").count() == 1
    assert "Currently clocked in" in employee_page.locator(".card-header").first.inner_text()
    employee_page.screenshot(path=SCREENSHOTS / "clock_in_active_card.png")


def test_clock_out_removes_active_card(employee_page, live_server):
    # Clock in first
    employee_page.click("button[type=submit]")
    employee_page.wait_for_selector("#active-entry-card")
    # Clock out
    employee_page.locator("button:has-text('Stop')").first.click()
    employee_page.wait_for_selector("#active-entry-card", state="detached")
    assert employee_page.locator("#active-entry-card").count() == 0
    # Success flash
    assert employee_page.locator(".alert-success").count() >= 1
    employee_page.screenshot(path=SCREENSHOTS / "after_clock_out.png")


def test_active_card_has_correct_link(employee_page, live_server):
    # Clock in
    employee_page.click("button[type=submit]")
    employee_page.wait_for_selector("#active-entry-card")
    # The "Edit / correct this entry" link should be present
    link = employee_page.locator("a:has-text('Edit / correct this entry')")
    assert link.count() == 1
    employee_page.screenshot(path=SCREENSHOTS / "clock_in_edit_link.png")


def test_correction_form_loads(employee_page, live_server):
    # Clock in
    employee_page.click("button[type=submit]")
    employee_page.wait_for_selector("#active-entry-card")
    # Navigate to correction form
    employee_page.locator("a:has-text('Edit / correct this entry')").click()
    employee_page.wait_for_selector("#start_time")
    assert "Correct active entry" in employee_page.locator("h1").inner_text()
    employee_page.screenshot(path=SCREENSHOTS / "correction_form.png")
