import argparse
import os
import re
from pathlib import Path
from playwright.sync_api import Playwright, sync_playwright, expect, Frame


def alias_exists(frame: Frame, alias: str) -> bool:
    """Return True if a keystore/truststore alias link is already visible in the list."""
    return frame.get_by_role("link", name=alias, exact=True).is_visible()


def fill_keystore_fields(frame: Frame, hostname: str, password: str, certificates: str) -> None:
    """Fill the keystore alias form fields (shared by create and edit flows)."""
    frame.get_by_label("Type", exact=True).select_option("PKCS12")
    frame.get_by_label("Provider").select_option("SUN")
    frame.get_by_role("textbox", name="Location").click()
    frame.get_by_role("textbox", name="Location").fill(str(Path(certificates) / f"{hostname}-keystore.p12"))
    frame.get_by_role("textbox", name="Password", exact=True).click()
    frame.get_by_role("textbox", name="Password", exact=True).fill(password)
    frame.get_by_role("textbox", name="Re-type Password").click()
    frame.get_by_role("textbox", name="Re-type Password").fill(password)


def fill_truststore_fields(frame: Frame, hostname: str, password: str, certificates: str) -> None:
    """Fill the truststore alias form fields (shared by create and edit flows)."""
    frame.get_by_label("Type", exact=True).select_option("PKCS12")
    frame.get_by_label("Provider").select_option("SUN")
    frame.get_by_role("textbox", name="Location").fill(str(Path(certificates) / f"{hostname}-truststore.p12"))
    frame.get_by_role("textbox", name="Password", exact=True).click()
    frame.get_by_role("textbox", name="Password", exact=True).fill(password)
    frame.get_by_role("textbox", name="Re-type Password").click()
    frame.get_by_role("textbox", name="Re-type Password").fill(password)


def run(playwright: Playwright, hostname: str, password: str, certificates: str) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto(f"http://{hostname}:5555/")
    page.get_by_role("textbox", name="Enter username").click()
    page.get_by_role("textbox", name="Enter username").fill("Administrator")
    page.get_by_role("textbox", name="Enter password").click()
    page.get_by_role("textbox", name="Enter password").fill("manage")
    page.get_by_role("button", name="Log in").click()
    page.get_by_test_id("ac.nav.label.security").click()
    page.get_by_test_id("ac.nav.label.securityKeystore").click()

    frame = page.locator("iframe[name=\"sagDSPFrame\"]").content_frame
    keystore_alias   = f"{hostname}_keystore"
    truststore_alias = f"{hostname}_truststore"

    # --- Keystore alias: create or edit ---
    if alias_exists(frame, keystore_alias):
        print(f"Keystore alias '{keystore_alias}' already exists — editing.")
        page.locator("iframe[name=\"sagDSPFrame\"]").content_frame.get_by_role("link", name=keystore_alias, exact=True).click()
        page.locator("iframe[name=\"sagDSPFrame\"]").content_frame.get_by_role("link", name="Edit Keystore Alias").click()
        fill_keystore_fields(frame, hostname, password, certificates)
        frame.get_by_role("textbox", name=hostname).click()
        frame.get_by_role("textbox", name=hostname).fill(password)
        frame.get_by_role("textbox", name="Re-type Password").click()
        frame.get_by_role("textbox", name="Re-type Password").fill(password)
        frame.get_by_role("button", name="Save Changes").click()
    else:
        print(f"Keystore alias '{keystore_alias}' not found — creating.")
        frame.get_by_role("link", name="Create Keystore Alias").click()
        frame.get_by_role("textbox", name="Alias").click()
        frame.get_by_role("textbox", name="Alias").fill(keystore_alias)
        fill_keystore_fields(frame, hostname, password, certificates)
        frame.get_by_role("button", name="Submit").click()
        frame.get_by_role("textbox", name=hostname).click()
        frame.get_by_role("textbox", name=hostname).fill(password)
        frame.get_by_role("textbox", name="Re-type Password").click()
        frame.get_by_role("textbox", name="Re-type Password").fill(password)
        frame.get_by_role("button", name="Save Changes").click()

    # --- Truststore alias: create or edit ---
    if alias_exists(frame, truststore_alias):
        print(f"Truststore alias '{truststore_alias}' already exists — editing.")
        page.locator("iframe[name=\"sagDSPFrame\"]").content_frame.get_by_role("link", name=truststore_alias, exact=True).click()
        page.locator("iframe[name=\"sagDSPFrame\"]").content_frame.get_by_role("link", name="Edit Keystore Alias").click()
        fill_truststore_fields(frame, hostname, password, certificates)
        frame.get_by_role("button", name="Save Changes").click()
    else:
        print(f"Truststore alias '{truststore_alias}' not found — creating.")
        frame.get_by_role("link", name="Create Truststore Alias").click()
        frame.get_by_role("textbox", name="Alias").click()
        frame.get_by_role("textbox", name="Alias").fill(truststore_alias)
        fill_truststore_fields(frame, hostname, password, certificates)
        frame.get_by_role("button", name="Save Changes").click()

    # Verify the aliases
    expect(frame.get_by_role("link", name=keystore_alias, exact=True)).to_be_visible()
    expect(frame.get_by_role("link", name=truststore_alias, exact=True)).to_be_visible()

    # ---------------------
    context.close()
    browser.close()


parser = argparse.ArgumentParser(description="Create IS keystore and truststore aliases via Playwright.")
parser.add_argument("-hostname", required=True, help="Hostname of the Integration Server (e.g. exxwin22sum25)")
parser.add_argument("-password", default="changeIt", help="Keystore/truststore password (default: changeIt)")
parser.add_argument("-certificates", default=".", help="Folder containing the .p12 certificate files (default: .)")
args = parser.parse_args()

with sync_playwright() as playwright:
    run(playwright, args.hostname, args.password, str(Path(args.certificates).resolve()))
