# zetaglobal.com — OneTrust CDN webform (privacyportal-cdn.onetrust.com).
# "I am an" (subjectTypesDSARElement) single-select toggle — "Email
# recipient or Internet user" used (vs. "Other"). "Select request type(s)"
# (requestTypesDSARElement) is GENUINELY multi-select (confirmed: two
# selections both stay highlighted) — all applicable rights checked in ONE
# combined submission: Request a copy of identifiable information
# (Access), Opt out of receiving email from Zeta on behalf of clients, Do
# not sell or share my identifiable information, Opt out of Zeta using
# sensitive information unconditionally; Delete identifiable information
# gated on REMOVE_INFORMATION. "Ask a question, report a problem, or file
# a complaint" skipped (nothing to report). No State field exists on this
# form (unlike most OneTrust CDN forms in this repo) — just Country.
# reCAPTCHA v2 — **CAPTCHA solution required**.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = (
    "https://privacyportal-cdn.onetrust.com/dsarwebform/bc2d3301-11a5-4de5-b15e-ce796187a352/"
    "d0720d0f-d427-4a7d-a773-5d6793229f15.html"
)

REQUEST_TYPES = [
    "Request a copy of identifiable information that relates to me",
    "Opt out of receiving email from Zeta on behalf of its clients",
    "Do not sell or share my identifiable information",
    "Opt out of Zeta using sensitive information that relates to me",
]
DELETE_REQUEST_TYPE = "Delete identifiable information that relates to me"


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

        await _select_option(tab, "Email recipient or Internet user", super_scraper, "'I am an'")

        for request_type in request_types:
            await _select_option(tab, request_type, super_scraper, "request type")

        first_field = await tab.find(id="firstNameDSARElement", raise_exc=False)
        if first_field:
            await first_field.type_text(SuperScraper.FIRST_NAME)
        else:
            print(f"{super_scraper.OOPS} First Name field not found")

        last_field = await tab.find(id="lastNameDSARElement", raise_exc=False)
        if last_field:
            await last_field.type_text(SuperScraper.LAST_NAME)
        else:
            print(f"{super_scraper.OOPS} Last Name field not found")

        email_field = await tab.find(id="emailDSARElement", raise_exc=False)
        if email_field:
            await email_field.type_text(SuperScraper.EMAIL)
        else:
            print(f"{super_scraper.OOPS} Email field not found")

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

        details_field = await tab.find(id="requestDetailsDSARElement", raise_exc=False)
        if details_field:
            request_text = "I am requesting access to and opting out of the sale/sharing of my personal information."
            if SuperScraper.REMOVE_INFORMATION:
                request_text += " I am also requesting deletion of my personal information."
            await details_field.type_text(request_text)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/zetaglobal_dry_run.png")
        print(
            "\nRequest filled but NOT submitted — a reCAPTCHA v2 checkbox requires a manual "
            "solve before submitting."
        )


asyncio.run(main())
