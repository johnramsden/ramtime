def test_delete_user_modal_flow(admin_page, live_server):
    """Create a user via the admin UI then delete them via the modal."""
    # Create a user to delete
    admin_page.goto(f"{live_server}/admin/users/new")
    admin_page.fill("input[name=name]", "To Delete")
    admin_page.fill("input[name=username]", "todelete")
    admin_page.fill("input[name=password]", "password123")
    admin_page.locator("button.btn-primary[type=submit]").click()
    admin_page.wait_for_url(f"{live_server}/admin/users")

    # Verify user appears in the table
    assert admin_page.locator("td", has_text="todelete").count() >= 1

    # Click the Delete button in the todelete row
    row = admin_page.locator("tr", has=admin_page.locator("td", has_text="todelete"))
    row.locator("button.btn-outline-danger").click()
    admin_page.wait_for_timeout(1000)  # brief wait for Bootstrap animation
    admin_page.screenshot(path="tests/browser/screenshots/delete_modal_debug.png")

    # Wait for modal to become visible
    admin_page.wait_for_selector(".modal.show", timeout=5000)

    # Fill in the username confirmation
    admin_page.locator(".modal.show input[name=confirm_name]").fill("todelete")

    # Click the Delete button in the modal
    admin_page.locator(".modal.show button.btn-danger").click()

    # Wait for redirect back to users page
    admin_page.wait_for_url(f"{live_server}/admin/users")
    admin_page.wait_for_load_state("networkidle")

    # User should no longer appear in the table
    assert admin_page.locator("td", has_text="todelete").count() == 0
