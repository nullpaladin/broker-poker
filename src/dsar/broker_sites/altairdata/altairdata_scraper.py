# altairdata.com — Jira Service Management customer portal (datacloudhome.atlassian.net).
# The portal's "Individual: Opt-Out/Deletion Request Form" requires checking a box
# attesting: "This form is intended for individual, manual submissions only... For
# high-volume or automated requests, we offer an enterprise API." A separate
# "Automation Request Form" exists, but it is a B2B integration-request form (asks
# for Company Name, no consumer PII fields) — not a mechanism to submit an actual
# opt-out. Since neither path lets a script both fill AND honestly submit on a
# consumer's behalf, this scraper fills every field but deliberately stops short of
# checking the "manual submission" attestation or clicking Submit, regardless of
# DRY_RUN — a human must review and finish it themselves.
# Checkboxes selected: Opt-Out of Sale, Opt-Out of Information Sharing, Opt-Out of
# Sensitive PI Use unconditionally; Deletion of My Consumer Information gated on
# REMOVE_INFORMATION. "Opt-Out of Postal Mailings to Deceased Persons" is skipped
# (not applicable). reCAPTCHA v2 checkbox also requires a manual solve.
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://datacloudhome.atlassian.net/servicedesk/customer/portal/12/group/35/create/158"

CHECKBOXES = [
    "Opt-Out of Sale of Personal Information",
    "Opt-Out of Information Sharing",
    "Opt-Out of Use of Sensitive Personal Information",
]
DELETE_CHECKBOX = "Deletion of My Consumer Information"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        cookie_accept = await tab.find(text="Accept all", raise_exc=False)
        if cookie_accept:
            await cookie_accept.click()
            await asyncio.sleep(1)

        email = await tab.find(id="email", raise_exc=False)
        if email:
            await email.type_text(SuperScraper.EMAIL)

        full_name = await tab.find(id="summary", raise_exc=False)
        if full_name:
            await full_name.type_text(f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")

        first = await tab.find(id="customfield_10354", raise_exc=False)
        if first:
            await first.type_text(SuperScraper.FIRST_NAME)

        last = await tab.find(id="customfield_10355", raise_exc=False)
        if last:
            await last.type_text(SuperScraper.LAST_NAME)

        address = await tab.find(id="customfield_10465", raise_exc=False)
        if address:
            await address.type_text(SuperScraper.ADDRESS)

        city = await tab.find(id="customfield_10466", raise_exc=False)
        if city:
            await city.type_text(SuperScraper.CITY)

        state = await tab.find(id="customfield_10467", raise_exc=False)
        if state:
            await state.type_text(SuperScraper.STATE)

        zip_field = await tab.find(id="customfield_10468", raise_exc=False)
        if zip_field:
            await zip_field.type_text(SuperScraper.ZIP_CODE)

        checkboxes = list(CHECKBOXES)
        if SuperScraper.REMOVE_INFORMATION:
            checkboxes.append(DELETE_CHECKBOX)
        for label in checkboxes:
            box = await tab.find(name=label, raise_exc=False)
            if box:
                await box.click()
                await asyncio.sleep(0.3)

        await asyncio.sleep(1)
        await tab.take_screenshot(path="resources/screenshots/altairdata_prefilled.png")
        print("Screenshot saved to resources/screenshots/altairdata_prefilled.png")
        print(
            "\nForm pre-filled but NOT submitted. Altair's portal requires checking an "
            "attestation that this is an individual, manual submission (not automated) "
            "before it will accept the request — that attestation and the reCAPTCHA "
            "must be completed by a human. Review the form, check the attestation "
            "boxes yourself, solve the reCAPTCHA, and click Submit in the browser."
        )


asyncio.run(main())
