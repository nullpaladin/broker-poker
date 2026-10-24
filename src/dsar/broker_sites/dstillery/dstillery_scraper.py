# dstillery.com — OneTrust EU CDN Angular form. Rights the form exposes (and we map):
# access, opt-out, delete. Which of them run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP).
# Subject type "A Consumer". formField18DSARElement is the Authorized Agent email
# (not required when submitting as consumer — left empty). reCAPTCHA v2 checkbox
# requires manual solve before submit. No country/state/phone/address fields.
#
# Page elements:
#   [aria-label="A Consumer"]        Subject type button
#   [aria-label=<request type>]      Request type buttons (labels in RIGHT_MAP)
#   #firstNameDSARElement / #lastNameDSARElement / #emailDSARElement   First / Last name, Email
#   #formField18DSARElement          Authorized Agent email (left empty)
#   [aria-label="click to submit form"]   Submit button
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal-eu-cdn.onetrust.com/dsarwebform/246426b7-49c6-4bf5-879b-d3fdd4cbc15d/35502283-7b19-4b67-b3e0-ede06d3820c5.html"

# (aria-label, screenshot label)
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("Access request", "access")],
    Right.RIGHT_TO_OPT_OUT: [("Opt-out request", "optout")],
    Right.RIGHT_TO_DELETE: [("Deletion request", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (Recorded request types are aria-labels; the visible text may differ, so they are not copied in.)

FIELD_XPATHS = {
    "First name": "//*[@id='firstNameDSARElement']",
    "Last name": "//*[@id='lastNameDSARElement']",
    "Email": "//*[@id='emailDSARElement']",
}


async def submit_request(tab, right, aria_label, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    consumer_btn = await tab.find(**{"aria-label": "A Consumer"}, raise_exc=False)
    if consumer_btn:
        await consumer_btn.click_using_js()
    await asyncio.sleep(1)

    req_btn = await tab.find(**{"aria-label": aria_label}, raise_exc=False)
    if not req_btn:
        print(f"{super_scraper.OOPS} Request button '{aria_label}' not found")
        return
    await req_btn.click_using_js()
    await asyncio.sleep(1)

    first = await tab.find(id="firstNameDSARElement", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)

    last = await tab.find(id="lastNameDSARElement", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)

    email = await tab.find(id="emailDSARElement", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    time.sleep(0.5)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    if SuperScraper.DRY_RUN:
        submit_btn = await tab.find(**{"aria-label": "click to submit form"}, raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
        print(f"DRY RUN: would submit '{right.name}' ({aria_label}) for {SuperScraper.EMAIL}")
        return

    print(f"\nForm filled for '{aria_label}'.")
    print("Solve the reCAPTCHA in the browser, then click Submit.")
    print("Press Enter after the confirmation page appears...")
    input()

    print(f"Submitted '{right.name}' ({aria_label}) for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()
    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            for aria_label, label in RIGHT_MAP[right]:
                await submit_request(tab, right, aria_label, label, super_scraper)


asyncio.run(main())
