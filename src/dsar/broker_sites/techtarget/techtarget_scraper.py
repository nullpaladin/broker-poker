# techtarget.com — Zendesk ticket form (ticket_form_id=360004852434, CCPA Privacy Rights Request Form).
# Rights the form exposes: access, opt-out of sale, delete. Which of them run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). Uses the CCPA form (covers equivalent rights for
# other states' residents). One submission per right.
# No CAPTCHA detected. Delete uses sub-option "Remove me from ALL databases".
# Tagger widget: hidden input + a.nesty-input trigger; li items use tagger value as id.
#
# Page elements:
#   #request_issue_type_select                 Issue type <select> -> option value 360004852434 (CCPA form)
#   #request_anonymous_requester_email         Email
#   #request_custom_fields_360055089353        First Name
#   #request_custom_fields_360055089373        Last Name
#   #request_custom_fields_360047462713        Request Type (nesty tagger; its next sibling is the trigger)
#   li.nesty-expand "Right to be DELETED"      expands the delete sub-options
#   input[name=commit]                         Submit button
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://techtarget.zendesk.com/hc/en-us/requests/new?ticket_form_id=360004852434"

# Right -> (tagger value, is_delete_sub_option)
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ("ccpa__right_to_access", False),
    Right.RIGHT_TO_OPT_OUT: ("ccpa__right_to_opt-out_of_sale", False),
    Right.RIGHT_TO_DELETE: ("ccpa__right_to_be_deleted__all_databases", True),
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


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


async def submit_request(tab, right, entry, super_scraper):
    tagger_value, is_delete = entry
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
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
        return

    submit_btn = await tab.find(tag_name="input", **{"name": "commit"}, raise_exc=False)
    if submit_btn:
        await submit_btn.click()
    await asyncio.sleep(5)

    print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, right, RIGHT_MAP[right], super_scraper)


asyncio.run(main())
