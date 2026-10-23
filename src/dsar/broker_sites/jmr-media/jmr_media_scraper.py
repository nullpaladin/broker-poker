# jmr-media.com — React/Next.js form with Cloudflare Turnstile that auto-completes
# in a real Chromium browser (no manual solve needed). Rights the form exposes:
# Access, Opt-Out of Sale/Share, Limit Sensitive PI, Delete (and Correct — not
# automated, needs the user to specify what to correct). Which rights run is
# decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP). One submission per
# radio choice.
#
# Page elements:
#   #firstName / #lastName / #email   First / Last name, Email
#   #state                            native <select>, 2-letter abbreviation values
#   input[name=requestType]           radio group (values in RIGHT_MAP)
#   "Submit Request" button           (falls back to the first <button>)
#   #website                          honeypot — not touched
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://jmr-media.com/do-not-sell"

# (requestType value, screenshot label)
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("access_request", "access")],
    Right.RIGHT_TO_OPT_OUT: [("opt_out_sale_share", "optout"), ("limit_sensitive_pi", "sensitive")],
    Right.RIGHT_TO_DELETE: [("delete_request", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
RIGHTS_OPTIONS_CSS = "label:has(input[name='requestType'])"

FIELD_XPATHS = {
    "First name": "//*[@id='firstName']",
    "Last name": "//*[@id='lastName']",
    "Email": "//*[@id='email']",
    "State": "//*[@id='state']",
}


async def submit_request(tab, right, request_value, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)  # allow Turnstile to auto-complete

    first = await tab.find(id="firstName", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)

    last = await tab.find(id="lastName", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)

    email = await tab.find(id="email", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    state_abbr = SuperScraper.STATE_ABBREVIATED
    state_select = await tab.find(id="state", raise_exc=False)
    if state_select:
        state_opt = await state_select.find(tag_name="option", value=state_abbr, raise_exc=False)
        if state_opt:
            await state_opt.click()

    if SuperScraper.HEALTH_CHECK:
        offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
        SuperScraper.audit_rights(offered, PAGE_RIGHTS)

    radio = await tab.find(
        xpath=f"//input[@name='requestType'][@value='{request_value}']",
        raise_exc=False,
    )
    if not radio:
        print(f"{super_scraper.OOPS} Radio '{request_value}' not found")
        return
    await radio.click()

    time.sleep(0.5)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right.name}' ({request_value}) for {SuperScraper.EMAIL}"
        )
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
        return

    submit = await tab.find(text="Submit Request", raise_exc=False)
    if not submit:
        submit = await tab.find(tag_name="button", raise_exc=False)
    if submit:
        await submit.click()
    await asyncio.sleep(4)

    print(f"Submitted '{right.name}' ({request_value}) for {SuperScraper.EMAIL} — confirm in the browser.")


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
            for request_value, label in RIGHT_MAP[right]:
                await submit_request(tab, right, request_value, label, super_scraper)


asyncio.run(main())
