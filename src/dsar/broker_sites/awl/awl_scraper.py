# awl.com (All Web Leads) — Custom OneTrust EU Angular DSAR portal. Subject
# type button aria-label is "For Myself" (not "Myself"). Request type is
# single-select (one submission per right): "Request to Know" (Access),
# "Request to Delete" (Delete); which run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). No address/state fields —
# just name, date of birth, phone, email, and a request-details textarea.
# reCAPTCHA v2 checkbox requires manual solve in live mode.
#
# Page elements (keep this list current):
#   role=button aria-label="For Myself"     Subject type
#   role=button aria-label=<request type>   "Request to Know" / "Request to Delete"
#   #firstNameDSARElement / #lastNameDSARElement   First / Last name
#   #dateOfBirthDSARElement     Date of birth (MM/DD/YYYY typed)
#   #vt-input-4                 Phone country code (typed "1")
#   #phoneNumberDSARElement     Phone number
#   #emailDSARElement           Email
#   #requestDetailsDSARElement  Request details textarea
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal-eu.onetrust.com/webform/031dc37f-2093-4055-9d04-22f83329fe9f/a4fb8ed6-8389-4a17-a3be-ca808c6b300e"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ("Request to Know", "access"),
    Right.RIGHT_TO_DELETE: ("Request to Delete", "delete"),
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (Recorded request types are aria-labels; the visible text may differ, so they are not copied in.)

FIELD_XPATHS = {
    "First name": "//*[@id='firstNameDSARElement']",
    "Last name": "//*[@id='lastNameDSARElement']",
    "Date of birth": "//*[@id='dateOfBirthDSARElement']",
    "Phone": "//*[@id='phoneNumberDSARElement']",
    "Email": "//*[@id='emailDSARElement']",
    "Request details": "//*[@id='requestDetailsDSARElement']",
}


async def submit_request(tab, right, right_label, screenshot_label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    myself_btn = await tab.find(**{"aria-label": "For Myself"}, raise_exc=False)
    if not myself_btn:
        print(f"{super_scraper.OOPS} 'For Myself' subject button not found")
        return
    await myself_btn.click_using_js()
    await asyncio.sleep(1)

    req_btn = await tab.find(**{"aria-label": right_label}, raise_exc=False)
    if not req_btn:
        print(f"{super_scraper.OOPS} Request type button '{right_label}' not found")
        return
    await req_btn.click_using_js()
    await asyncio.sleep(1)

    first = await tab.find(id="firstNameDSARElement", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)

    last = await tab.find(id="lastNameDSARElement", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)

    if SuperScraper.DATE_OF_BIRTH:
        day, month, year = SuperScraper.DATE_OF_BIRTH.split("/")
        dob = await tab.find(id="dateOfBirthDSARElement", raise_exc=False)
        if dob:
            await dob.type_text(f"{month}/{day}/{year}")

    phone_cc = await tab.find(id="vt-input-4", raise_exc=False)
    if phone_cc:
        await phone_cc.click()
        await tab.keyboard.type_text("1")
    await asyncio.sleep(0.5)

    phone = await tab.find(id="phoneNumberDSARElement", raise_exc=False)
    if phone:
        await phone.type_text(SuperScraper.PHONE_NUMBER)

    email = await tab.find(id="emailDSARElement", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    request_details = await tab.find(id="requestDetailsDSARElement", raise_exc=False)
    if request_details:
        await request_details.type_text(SuperScraper.request_statement([right], broker="All Web Leads"))

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}"
        )
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{screenshot_label}")
        return

    print(f"\nForm filled for '{right.name}'. Solve the reCAPTCHA, click Submit,")
    print("then press Enter once the confirmation page appears...")
    input()

    print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


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
            right_label, screenshot_label = RIGHT_MAP[right]
            await submit_request(tab, right, right_label, screenshot_label, super_scraper)


asyncio.run(main())
