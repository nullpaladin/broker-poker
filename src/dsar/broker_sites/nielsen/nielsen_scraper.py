# nielsen.com — OneTrust CDN DSAR webform (privacyportalde-cdn.onetrust.com),
# same template/element ids as zetaglobal.com elsewhere in this repo. A prior manual
# investigation recorded this URL as redirecting to google.com — that no longer reproduces;
# the form now loads normally. Rights the form exposes: Request my personal information
# (Access), Delete my personal information, Correct (not automated), Other (not automated).
# Request type is genuinely SINGLE-select (confirmed: picking a second option un-highlights
# the first) — one submission per right. Which rights run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). BotDetect image CAPTCHA —
# **CAPTCHA solution required**, so the form is filled and never submitted.
#
# Page elements (keep this list current):
#   #subjectTypesDSARElement            "I am a (an)" chooser; options are Prospective/Former Employee,
#                                       Panel Member, Former Panel Member, Survey respondent, Other
#                                       (no generic consumer option) -> "Other"
#   #firstNameDSARElement / #lastNameDSARElement / #emailDSARElement   First / Last name, Email
#   #countryDSARElement                 Country autocomplete (fill first; reveals State and request types)
#   #stateDSARElement                   State autocomplete (expects the full US state name)
#   "Select Request Type" option divs   -> see RIGHT_MAP
#   #requestDetailsDSARElement          Request details textarea
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = (
    "https://privacyportalde-cdn.onetrust.com/dsarwebform/70b0083d-d519-4ad2-84ca-96b7c5f8e1a9/"
    "9810a8bc-e54d-4d70-bac0-5e4d781ef5b9.html"
)

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Request my personal information",
    Right.RIGHT_TO_DELETE: "Delete my personal information",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (Only two request-type texts are recorded verbatim; Correct and Other are not.)

FIELD_XPATHS = {
    "First name": "//*[@id='firstNameDSARElement']",
    "Last name": "//*[@id='lastNameDSARElement']",
    "Email": "//*[@id='emailDSARElement']",
    "Country": "//*[@id='countryDSARElement']",
    "State": "//*[@id='stateDSARElement']",
    "Request details": "//*[@id='requestDetailsDSARElement']",
}


async def _select_autocomplete(tab, field_id, value, super_scraper, description):
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        print(f"{super_scraper.OOPS} {description} field not found")
        return
    await field.click()
    await asyncio.sleep(0.3)
    await tab.keyboard.type_text(value)
    await asyncio.sleep(1.2)
    option = await tab.find(xpath=f"//*[@role='option' and normalize-space()={value!r}]", raise_exc=False)
    if option:
        await option.click()
        await asyncio.sleep(0.7)
    else:
        print(f"{super_scraper.OOPS} {description} option '{value}' not found")


async def submit_request(tab, right, request_type_text, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    other = await tab.find(xpath="//div[@id='subjectTypesDSARElement']//div[normalize-space(.)='Other']", raise_exc=False)
    if other:
        await other.click()
    else:
        print(f"{super_scraper.OOPS} 'I am a (an)' Other option not found")

    fields = {
        "firstNameDSARElement": SuperScraper.FIRST_NAME,
        "lastNameDSARElement": SuperScraper.LAST_NAME,
        "emailDSARElement": SuperScraper.EMAIL,
    }
    for field_id, value in fields.items():
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    await _select_autocomplete(tab, "countryDSARElement", "United States", super_scraper, "Country")
    await _select_autocomplete(tab, "stateDSARElement", SuperScraper.STATE, super_scraper, "State")

    request_type = await tab.find(
        xpath=f"//div[normalize-space(.)={request_type_text!r}]", raise_exc=False
    )
    if request_type:
        await request_type.click()
    else:
        print(f"{super_scraper.OOPS} Request type '{request_type_text}' not found")

    details_field = await tab.find(id="requestDetailsDSARElement", raise_exc=False)
    if details_field:
        await details_field.type_text(SuperScraper.request_statement([right], broker="Nielsen"))

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
    print(
        f"\n'{request_type_text}' request filled but NOT submitted — a BotDetect image CAPTCHA "
        "requires manual entry before submitting."
    )


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    if SuperScraper.bail_if_not_automatable(globals()):
        return
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, right, RIGHT_MAP[right], super_scraper)


asyncio.run(main())
