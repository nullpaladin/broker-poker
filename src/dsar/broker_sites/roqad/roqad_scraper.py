# roq.ad — the marketing page (roq.ad/privacy-form) only embeds a
# non-frame-busting iframe; navigate directly to the underlying OneTrust
# webform: https://roqad-privacy.my.onetrust.com/webform/bdcc4a2f-2458-
# 4e17-96c3-cf88f7115dfc/dcc653f1-96d6-4d0f-ba5d-cb7f17fff0aa (shared
# ROQAD/Zeotap portal). "Select request type(s)" is a GENUINELY
# multi-select role="option" toggle group (confirmed: selecting a second
# option doesn't deselect the first) — all applicable rights checked in
# ONE combined submission, unlike most sites in this repo. Options: Data
# deletion (gated on REMOVE_INFORMATION), Opt out and Info request
# (unconditional), File a complaint (skipped — no complaint to file).
# "I am a (an)" answered "Consumer/ Data subject". Country is a
# vt-autocomplete combobox. Four optional device-identifier fields
# (Cookie ID, iOS IDFA, Android AAID, Hashed Email) appear in that DOM
# order as formField79-82DSARElement — this repo's single generic
# ADVERTISING_ID is filled into AAID (Android) as the closest match, same
# "defaults to the Android identifier" precedent used elsewhere in this
# repo for sites offering multiple MAID-type slots; Cookie ID/IDFA/HEM are
# left blank (no equivalent persona data). Required free-text "Request
# details" filled generically. reCAPTCHA v2 — **CAPTCHA solution
# required**.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://roqad-privacy.my.onetrust.com/webform/bdcc4a2f-2458-4e17-96c3-cf88f7115dfc/dcc653f1-96d6-4d0f-ba5d-cb7f17fff0aa"

REQUEST_TYPES = ["Opt out", "Info request"]
DELETE_REQUEST_TYPE = "Data deletion"


async def _select_option(tab, option_text, super_scraper, description):
    option = await tab.find(xpath=f"//*[@role='option' and normalize-space()='{option_text}']", raise_exc=False)
    if option:
        await option.click()
        await asyncio.sleep(0.5)
    else:
        print(f"{super_scraper.OOPS} {description} option '{option_text}' not found")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    request_types = list(REQUEST_TYPES)
    if SuperScraper.REMOVE_INFORMATION:
        request_types.append(DELETE_REQUEST_TYPE)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        country_field = await tab.find(id="countryDSARElement", raise_exc=False)
        if country_field:
            await country_field.click()
            await asyncio.sleep(0.3)
            await tab.keyboard.type_text("United States")
            await asyncio.sleep(1.2)
            option = await tab.find(xpath="//*[@role='option' and normalize-space()='United States']", raise_exc=False)
            if option:
                await option.click()
                await asyncio.sleep(0.7)
            else:
                print(f"{super_scraper.OOPS} country option 'United States' not found")
        else:
            print(f"{super_scraper.OOPS} Country field not found")

        for request_type in request_types:
            await _select_option(tab, request_type, super_scraper, "request type")

        await _select_option(tab, "Consumer/ Data subject", super_scraper, "'I am a (an)'")

        first_field = await tab.find(id="firstNameDSARElement", raise_exc=False)
        if first_field:
            await first_field.type_text(SuperScraper.FIRST_NAME)
        last_field = await tab.find(id="lastNameDSARElement", raise_exc=False)
        if last_field:
            await last_field.type_text(SuperScraper.LAST_NAME)
        email_field = await tab.find(id="emailDSARElement", raise_exc=False)
        if email_field:
            await email_field.type_text(SuperScraper.EMAIL)

        aaid_field = await tab.find(id="formField81DSARElement", raise_exc=False)
        if aaid_field and SuperScraper.ADVERTISING_ID:
            await aaid_field.type_text(SuperScraper.ADVERTISING_ID)

        details_field = await tab.find(id="requestDetailsDSARElement", raise_exc=False)
        if details_field:
            request_text = "I am requesting access to my personal information."
            if SuperScraper.REMOVE_INFORMATION:
                request_text = "I am requesting access to and deletion of my personal information."
            await details_field.type_text(request_text)

        await asyncio.sleep(1)
        await tab.take_screenshot(path="resources/screenshots/roqad_dry_run.png")
        print("Screenshot saved to resources/screenshots/roqad_dry_run.png")
        print(
            "\nRequest filled but NOT submitted — a reCAPTCHA v2 checkbox requires a manual "
            "solve before submitting."
        )


asyncio.run(main())
