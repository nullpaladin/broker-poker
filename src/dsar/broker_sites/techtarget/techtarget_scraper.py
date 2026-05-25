# techtarget.com — exercises Access, Opt-Out of Sale/Sharing, Delete (gated).
# Zendesk ticket form (ticket_form_id=360004852434, CCPA Privacy Rights Request Form).
# Uses CCPA form (covers equivalent MCDPA rights for MN residents). One submission per right.
# Fields: email, First Name, Last Name, Request Type (Zendesk nesty tagger widget).
# No CAPTCHA detected. Delete uses sub-option "Remove me from ALL databases".
# Tagger widget: hidden input + a.nesty-input trigger; li items use tagger value as id.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://techtarget.zendesk.com/hc/en-us/requests/new?ticket_form_id=360004852434"

# (tagger value, is_delete_sub_option, screenshot label)
REQUESTS = [
    ("ccpa__right_to_access",           False, "access"),
    ("ccpa__right_to_opt-out_of_sale",  False, "optout"),
]
DELETE_REQUEST = ("ccpa__right_to_be_deleted__all_databases", True, "delete")


async def _open_tagger(tab):
    """Open the request type nesty tagger dropdown."""
    await tab.execute_script(
        "document.getElementById('request_custom_fields_360047462713').nextElementSibling.click();"
    )
    await asyncio.sleep(1)


async def _select_tagger_value(tab, value):
    """Select a top-level tagger option by its id (== tagger value)."""
    await _open_tagger(tab)
    req_li = await tab.find(id=value, raise_exc=False)
    if req_li:
        await req_li.click()
    else:
        print(f"  Tagger li '{value}' not found")
    await asyncio.sleep(0.5)


async def _select_tagger_delete(tab, child_value):
    """Expand 'Right to be DELETED' and select the sub-option by id."""
    await _open_tagger(tab)
    await tab.execute_script("""
        var lis = document.querySelectorAll('li.nesty-expand');
        for (var li of lis) {
            if (li.textContent.trim() === 'Right to be DELETED') {
                li.click();
                break;
            }
        }
    """)
    await asyncio.sleep(0.8)
    child_li = await tab.find(id=child_value, raise_exc=False)
    if child_li:
        await child_li.click()
    else:
        print(f"  Delete sub-option li '{child_value}' not found")
    await asyncio.sleep(0.5)


async def submit_request(tab, tagger_value, is_delete, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    # Select CCPA Privacy Rights Request Form from the issue type dropdown
    issue_sel = await tab.find(tag_name="select", id="request_issue_type_select", raise_exc=False)
    if issue_sel:
        opt = await issue_sel.find(tag_name="option", value="360004852434", raise_exc=False)
        if opt:
            await opt.click()
            await asyncio.sleep(3)

    email_field = await tab.find(id="request_anonymous_requester_email", raise_exc=False)
    if email_field:
        await email_field.type_text(SuperScraper.EMAIL)

    first = await tab.find(id="request_custom_fields_360055089353", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)

    last = await tab.find(id="request_custom_fields_360055089373", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)

    if is_delete:
        await _select_tagger_delete(tab, tagger_value)
    else:
        await _select_tagger_value(tab, tagger_value)

    time.sleep(0.5)

    if SuperScraper.DRY_RUN:
        submit_btn = await tab.find(tag_name="input", **{"name": "commit"}, raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await tab.take_screenshot(f"techtarget_dry_run_{label}.png")
        print(
            f"DRY RUN: would submit '{label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        return

    submit_btn = await tab.find(tag_name="input", **{"name": "commit"}, raise_exc=False)
    if submit_btn:
        await submit_btn.click()
    await asyncio.sleep(5)

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "submitted", "received", "ticket", "confirmation")):
        print(f"Submitted '{label}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{label}' — verify in browser")


async def main():
    options = ChromiumOptions()
    options.binary_location = "/snap/bin/chromium"
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,2000")
    super_scraper = SuperScraper()

    requests = list(REQUESTS)
    if SuperScraper.REMOVE_INFORMATION:
        requests.append(DELETE_REQUEST)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for tagger_value, is_delete, label in requests:
            await submit_request(tab, tagger_value, is_delete, label, super_scraper)


asyncio.run(main())
