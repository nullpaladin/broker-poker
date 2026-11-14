# mediaocean.com — Marketo form (mktoForm_3843) at /your-privacy-rights. One submission per right.
# Rights the form exposes (via the cCPARequest select): "CCPA Obtain Info" (access),
# "CCPA Opt Out of Sale" (opt-out), "CCPA Delete Info" (delete). Which of them run is decided
# ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP). No CAPTCHA detected.
#
# Page elements (keep this list current):
#   "Reject all cookies"     cookie banner button (clicked if present and visible)
#   #FirstName / #LastName   First / Last name
#   #Email                   Email
#   #State                   State <select> (full state name, e.g. "Minnesota")
#   #areYoutheConsumer       "Are you the consumer" <select> -> "Yes"
#   #cCPARequest             Request type <select> -> RIGHT_MAP option values
#   "Submit" button          found by its text
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.mediaocean.com/your-privacy-rights"

FIRST_NAME_ID = "FirstName"  # First name
LAST_NAME_ID = "LastName"  # Last name
EMAIL_ID = "Email"  # Email
STATE_ID = "State"  # State <select>
CONSUMER_ID = "areYoutheConsumer"  # "Are you the consumer" <select>
REQUEST_TYPE_ID = "cCPARequest"  # Request type <select>

# Right -> cCPARequest option value
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "CCPA Obtain Info",
    Right.RIGHT_TO_OPT_OUT: "CCPA Opt Out of Sale",
    Right.RIGHT_TO_DELETE: "CCPA Delete Info",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
RIGHTS_OPTIONS_CSS = f"#{REQUEST_TYPE_ID} option"  # option texts may differ from the recorded option values

FIELD_XPATHS = {
    "First name": f"//*[@id='{FIRST_NAME_ID}']",
    "Last name": f"//*[@id='{LAST_NAME_ID}']",
    "Email": f"//*[@id='{EMAIL_ID}']",
    "State": f"//*[@id='{STATE_ID}']",
    "Are you the consumer": f"//*[@id='{CONSUMER_ID}']",
    "Request type": f"//*[@id='{REQUEST_TYPE_ID}']",
}


async def submit_request(tab, right, ccpa_value, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    # Dismiss cookie banner if present and visible
    reject = await tab.find(text="Reject all cookies", raise_exc=False)
    if reject and await reject.is_visible():
        await reject.click()
        await asyncio.sleep(1)

    if SuperScraper.HEALTH_CHECK:
        offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
        SuperScraper.audit_rights(offered, PAGE_RIGHTS)

    first = await tab.find(id=FIRST_NAME_ID, raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)

    last = await tab.find(id=LAST_NAME_ID, raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)

    email = await tab.find(id=EMAIL_ID, raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    # State: native <select> with full state name values
    state_select = await tab.find(tag_name="select", id=STATE_ID, raise_exc=False)
    if state_select:
        state_opt = await state_select.find(
            tag_name="option", value=SuperScraper.STATE.title(), raise_exc=False
        )
        if state_opt:
            await state_opt.click()

    # Are you the consumer: "Yes"
    consumer_select = await tab.find(tag_name="select", id=CONSUMER_ID, raise_exc=False)
    if consumer_select:
        yes_opt = await consumer_select.find(tag_name="option", value="Yes", raise_exc=False)
        if yes_opt:
            await yes_opt.click()

    # Request type
    ccpa_select = await tab.find(tag_name="select", id=REQUEST_TYPE_ID, raise_exc=False)
    if ccpa_select:
        ccpa_opt = await ccpa_select.find(tag_name="option", value=ccpa_value, raise_exc=False)
        if ccpa_opt:
            await ccpa_opt.click()
    else:
        print(f"{super_scraper.OOPS} cCPARequest select not found")
        return

    time.sleep(0.5)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    if SuperScraper.DRY_RUN:
        submit_btn = await tab.find(tag_name="button", text="Submit", raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        print(
            f"DRY RUN: would submit '{right.name}' ({ccpa_value}) for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        return

    submit_btn = await tab.find(tag_name="button", text="Submit", raise_exc=False)
    if submit_btn:
        await submit_btn.click()
    await asyncio.sleep(5)

    print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return
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
