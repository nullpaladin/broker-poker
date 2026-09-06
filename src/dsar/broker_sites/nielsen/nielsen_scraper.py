# nielsen.com — OneTrust CDN DSAR webform (privacyportalde-cdn.onetrust.com),
# same template/element ids as zetaglobal.com elsewhere in this repo
# (firstNameDSARElement/emailDSARElement/countryDSARElement/etc.). A prior
# manual investigation recorded this URL as redirecting to google.com — that
# no longer reproduces; the form now loads normally. "I am a (an)"
# (subjectTypesDSARElement) has no generic consumer option (Prospective/
# Former Employee, Panel Member, Former Panel Member, Survey respondent,
# Other) — "Other" used. Country must be filled first (vt-autocomplete) to
# reveal State (also vt-autocomplete, expects the full US state name) and
# "Select Request Type", which is genuinely SINGLE-select here (confirmed:
# picking a second option un-highlights the first) — one submission per
# right: Request my personal information (Access) unconditionally; Delete my
# personal information gated on REMOVE_INFORMATION. Correct skipped (no
# concrete inaccuracy to describe), Other skipped. BotDetect image CAPTCHA —
# **CAPTCHA solution required**.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = (
    "https://privacyportalde-cdn.onetrust.com/dsarwebform/70b0083d-d519-4ad2-84ca-96b7c5f8e1a9/"
    "9810a8bc-e54d-4d70-bac0-5e4d781ef5b9.html"
)

RIGHTS = [("Request my personal information", "access")]
DELETE_RIGHT = ("Delete my personal information", "delete")


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


async def submit_request(tab, request_type_text, label, super_scraper):
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
        await details_field.type_text(f"I am requesting to {request_type_text.lower()}.")

    await asyncio.sleep(1)
    await tab.take_screenshot(path=f"resources/screenshots/nielsen_dry_run_{label}.png")
    print(f"Screenshot saved to resources/screenshots/nielsen_dry_run_{label}.png")
    print(
        f"\n'{request_type_text}' request filled but NOT submitted — a BotDetect image CAPTCHA "
        "requires manual entry before submitting."
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,3000")

    rights = list(RIGHTS)
    if SuperScraper.REMOVE_INFORMATION:
        rights.append(DELETE_RIGHT)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for request_type_text, label in rights:
            await submit_request(tab, request_type_text, label, super_scraper)


asyncio.run(main())
