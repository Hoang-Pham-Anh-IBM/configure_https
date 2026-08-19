import argparse
import re
from playwright.sync_api import Playwright, sync_playwright, expect, Frame


def port_exists(frame: Frame, port: str) -> bool:
    """Return True if a row for this port number is already in the port list."""
    return frame.locator(f"a[href*='@{port}'][href*='editaccess']").is_visible()


def edit_port_fields(frame: Frame, hostname: str, alias: str) -> None:
    """Fill keystore/truststore alias selects and the port alias field."""
    frame.get_by_role("radio", name="Yes").check()
    frame.get_by_label("Keystore Alias").select_option(f"{hostname}_keystore")
    frame.get_by_label("Truststore Alias").select_option(f"{hostname}_truststore")

def fill_port_fields(frame: Frame, hostname: str, alias: str) -> None:
    """Fill keystore/truststore alias selects and the port alias field."""
    frame.get_by_role("textbox", name="Alias").click()
    frame.get_by_role("textbox", name="Alias").fill(alias)
    frame.get_by_role("radio", name="Yes").check()
    frame.get_by_label("Keystore Alias").select_option(f"{hostname}_keystore")
    frame.get_by_label("Truststore Alias").select_option(f"{hostname}_truststore")


def go_to_port_list(page) -> None:
    """Navigate back to the port list, tolerating being already there."""
    frame = page.locator("iframe[name=\"sagDSPFrame\"]").content_frame
    back = frame.get_by_role("link", name="Return to Port List")
    if back.is_visible():
        back.click()
    else:
        page.get_by_test_id("ac.nav.label.ports").click()


def set_access_mode_allow(page, port: str) -> None:
    """Click Deny+ for the given port, confirm the dialog, then set Allow by Default."""
    # Make sure we are on the port list page first
    go_to_port_list(page)

    frame = page.locator("iframe[name=\"sagDSPFrame\"]").content_frame
    deny_link = frame.locator(f"a[href*='@{port}'][href*='editaccess']")

    # Wait until the port list row is present
    deny_link.wait_for()

    # Only click if the link text contains "Deny" — skip if already "Allow"
    if "Deny" in deny_link.inner_text():
        page.once("dialog", lambda dialog: dialog.accept())  # register BEFORE click
        deny_link.click()
        frame.get_by_role("link", name="Set Access Mode to Allow by Default").click()
        frame.get_by_role("link", name="Return to Port List").click()


def run(playwright: Playwright, hostname: str, port: str, alias: str) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto(f"http://{hostname}:5555/")
    page.get_by_role("textbox", name="Enter username").click()
    page.get_by_role("textbox", name="Enter username").fill("Administrator")
    page.get_by_role("textbox", name="Enter password").click()
    page.get_by_role("textbox", name="Enter password").fill("manage")
    page.get_by_role("button", name="Log in").click()
    page.get_by_test_id("ac.nav.label.server").click()
    page.get_by_test_id("ac.nav.label.ports").click()

    frame = page.locator("iframe[name=\"sagDSPFrame\"]").content_frame

    if port_exists(frame, port):
        # --- Edit existing port ---
        print(f"Port {port} already exists — editing.")
        frame.get_by_role("link", name=port, exact=True).click()
        page.once("dialog", lambda dialog: dialog.accept())
        frame.get_by_role("link", name="Edit HTTPS Port Configuration").click()
        edit_port_fields(frame, hostname, alias)
        frame.get_by_role("button", name="Save Changes").click()
        #frame.get_by_role("link", name="Return to Port List").click()
    else:
        # --- Add new port ---
        print(f"Port {port} not found — creating.")
        frame.get_by_role("link", name="Add Port").click()
        frame.get_by_role("radio", name="webMethods/HTTPS").check()
        frame.get_by_role("button", name="Submit").click()
        frame.get_by_role("radio", name="Yes").check()
        frame.get_by_role("textbox", name="Port").click()
        frame.get_by_role("textbox", name="Port").fill(port)
        fill_port_fields(frame, hostname, alias)
        frame.get_by_role("button", name="Save Changes").click()
        #frame.get_by_role("link", name="Return to Port List").click()

    # --- Set access mode to Allow by Default ---
    set_access_mode_allow(page, port)

    # ---------------------
    context.close()
    browser.close()


parser = argparse.ArgumentParser(description="Configure IS HTTPS port aliases via Playwright.")
parser.add_argument("-hostname", required=True, help="Hostname of the Integration Server (e.g. exxwin22sum25)")
parser.add_argument("-port", required=True, help="HTTPS port number (e.g. 5577)")
parser.add_argument("-alias", required=True, help="Port alias name (e.g. CU_HTTPS_PORT)")
args = parser.parse_args()

with sync_playwright() as playwright:
    run(playwright, args.hostname, args.port, args.alias)
