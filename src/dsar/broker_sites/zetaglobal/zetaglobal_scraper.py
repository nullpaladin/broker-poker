# zetaglobal.com — OneTrust CDN webform (privacyportal-cdn.onetrust.com).
# "I am an" (subjectTypesDSARElement) single-select toggle — "Email
# recipient or Internet user" used (vs. "Other"). "Select request type(s)"
# (requestTypesDSARElement) is GENUINELY multi-select (confirmed: two
# selections both stay highlighted) — all applicable rights checked in ONE
# combined submission: Request a copy of identifiable information
# (Access), Opt out of receiving email from Zeta on behalf of clients, Do
# not sell or share my identifiable information, Opt out of Zeta using
# sensitive information; Delete identifiable information. Which of them are
# selected is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# "Ask a question, report a problem, or file a complaint" is not automated. No State field exists on this
# form (unlike most OneTrust CDN forms in this repo) — just Country.
# reCAPTCHA v2 — **CAPTCHA solution required**.
#
# Page elements:
#   #subjectTypesDSARElement     "I am an" toggle ("Email recipient or Internet user")
#   #requestTypesDSARElement     "Select request type(s)" options (see RIGHT_MAP)
#   #firstNameDSARElement / #lastNameDSARElement   First / Last name
#   #emailDSARElement            Email
#   #countryDSARElement          Country (-> "United States")
#   #requestDetailsDSARElement   Request details textarea
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = (
    "https://privacyportal-cdn.onetrust.com/dsarwebform/bc2d3301-11a5-4de5-b15e-ce796187a352/"
    "d0720d0f-d427-4a7d-a773-5d6793229f15.html"
)

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Request a copy of identifiable information that relates to me",
    Right.RIGHT_TO_OPT_OUT: [
        "Do not sell or share my identifiable information",
        "Opt out of receiving email from Zeta on behalf of its clients",
        "Opt out of Zeta using sensitive information that relates to me",
    ],
    Right.RIGHT_TO_DELETE: "Delete identifiable information that relates to me",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every option in the "Select request type(s)" group, as displayed -> the Right it maps to (None = not automated).
PAGE_RIGHTS = {
    "Request a copy of identifiable information that relates to me": Right.RIGHT_TO_ACCESS,
    "Do not sell or share my identifiable information": Right.RIGHT_TO_OPT_OUT,
    "Opt out of receiving email from Zeta on behalf of its clients": Right.RIGHT_TO_OPT_OUT,
    "Opt out of Zeta using sensitive information that relates to me": Right.RIGHT_TO_OPT_OUT,
    "Delete identifiable information that relates to me": Right.RIGHT_TO_DELETE,
    "Ask a question, report a problem, or file a complaint": None,
}
RIGHTS_OPTIONS_CSS = "#requestTypesDSARElement [role='option']"

FIELD_XPATHS = {
    "First name": "//*[@id='firstNameDSARElement']",
    "Last name": "//*[@id='lastNameDSARElement']",
    "Email": "//*[@id='emailDSARElement']",
    "Country": "//*[@id='countryDSARElement']",
    "Request details": "//*[@id='requestDetailsDSARElement']",
}


async def _select_option(tab, option_text, super_scraper, description):
    option = await tab.find(xpath=f"//*[@role='option' and normalize-space()='{option_text}']", raise_exc=False)
    if option:
        await option.click()
        await asyncio.sleep(0.5)
    else:
        print(f"{super_scraper.OOPS} {description} option '{option_text}' not found")


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    if SuperScraper.bail_if_not_automatable(globals()):
        return
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    request_types = []
    for right in rights:
        entries = RIGHT_MAP[right]
        request_types += entries if isinstance(entries, list) else [entries]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        if SuperScraper.HEALTH_CHECK:
            offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
            SuperScraper.audit_rights(offered, PAGE_RIGHTS)

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
            await details_field.type_text(SuperScraper.request_statement(rights, broker="Zeta Global"))

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run")
        print(
            "\nRequest filled but NOT submitted — a reCAPTCHA v2 checkbox requires a manual "
            "solve before submitting."
        )


asyncio.run(main())
