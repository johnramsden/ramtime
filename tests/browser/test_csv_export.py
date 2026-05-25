from pathlib import Path

SCREENSHOTS = Path(__file__).parent / "screenshots"


def test_export_button_visible(admin_page, live_server):
    btn = admin_page.locator("#export-btn")
    assert btn.count() == 1
    assert btn.is_visible()
    admin_page.screenshot(path=SCREENSHOTS / "csv_export_button.png")


def test_export_triggers_download(admin_page, live_server):
    with admin_page.expect_download() as download_info:
        admin_page.click("#export-btn")
    download = download_info.value
    assert download.suggested_filename.endswith(".csv")
    admin_page.screenshot(path=SCREENSHOTS / "csv_download_triggered.png")


def test_export_filename_contains_month(admin_page, live_server):
    # Get the current month from the export button href
    href = admin_page.locator("#export-btn").get_attribute("href")
    assert "month=" in href

    with admin_page.expect_download() as download_info:
        admin_page.click("#export-btn")
    download = download_info.value
    # Filename should be ramtime_YYYY-MM.csv
    assert download.suggested_filename.startswith("ramtime_")
    assert download.suggested_filename.endswith(".csv")
    admin_page.screenshot(path=SCREENSHOTS / "csv_filename.png")
