# awl.com (All Web Leads) — Custom OneTrust EU Angular DSAR portal. Subject
# type button aria-label is "For Myself" (not "Myself"). Request type is
# single-select (one submission per right): "Request to Know" (Access),
# "Request to Delete" (gated on REMOVE_INFORMATION). No address/state fields —
# just name, date of birth, phone, email, and a request-details textarea.
# reCAPTCHA v2 checkbox requires manual solve in live mode.
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal-eu.onetrust.com/webform/031dc37f-2093-4055-9d04-22f83329fe9f/a4fb8ed6-8389-4a17-a3be-ca808c6b300e"

RIGHTS = [("Request to Know", "access")]
DELETE_RIGHT = ("Request to Delete", "delete")


async def submit_request(tab, right_label, screenshot_label, super_scraper):
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
        await request_details.type_text(
            f"I am exercising my {right_label.lower()} rights under applicable privacy law."
        )

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right_label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/awl_dry_run_{screenshot_label}.png")
        return

    print(f"\nForm filled for '{right_label}'. Solve the reCAPTCHA, click Submit,")
    print("then press Enter once the confirmation page appears...")
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{right_label}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{right_label}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    rights = list(RIGHTS)
    if SuperScraper.REMOVE_INFORMATION:
        rights.append(DELETE_RIGHT)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right_label, screenshot_label in rights:
            await submit_request(tab, right_label, screenshot_label, super_scraper)


asyncio.run(main())
