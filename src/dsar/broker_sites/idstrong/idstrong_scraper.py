# idstrong.com — the /privacyform/ page embeds a OneTrust EU DSAR webform in an
# iframe; this navigates straight to that webform URL (the visible people-search
# name box on the wrapper page is NOT the DSAR form).
#
# Standard OneTrust webform:
#   countryDSARElement / stateDSARElement / cityDSARElement  autocomplete
#       comboboxes (type, then ArrowDown+Enter to commit the match)
#   subjectTypesDSARElement  "I am submitting on behalf of" -> "Myself"
#   requestTypesDSARElement   SINGLE-select role="option" group (picking a
#       second option deselects the first), so this submits one request per
#       right: Access + Opt-Out + Data Portability unconditionally; Delete
#       gated on REMOVE_INFORMATION; Correct skipped.
#   firstNameDSARElement / lastNameDSARElement / emailDSARElement
#   dateOfBirthDSARElement  required date picker (MM/DD/YYYY, converted from the
#       .env DD/MM/YYYY)
#   An optional ID-document upload (only needed for authorised-agent requests)
#       is left blank.
# reCAPTCHA gates the submit — every field is filled and the form is left for a
# manual solve.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = (
    "https://privacyportal-eu.onetrust.com/webform/"
    "f6adb000-5a85-4ec1-a631-151c15d9d854/cbee3ef7-0c4c-44c0-b897-a08a9c4c1d62"
)

RIGHTS = [
    ("Request Access to Personal Information", "access"),
    ("Request to Opt-Out (Do Not Sell or Share My Personal Information)", "opt_out"),
    ("Request to Data Portability", "portability"),
]
DELETE_RIGHT = ("Request to Delete Personal Information", "delete")


def _dob_mm_dd_yyyy():
    if not SuperScraper.DATE_OF_BIRTH:
        return ""
    parts = SuperScraper.DATE_OF_BIRTH.split("/")
    if len(parts) != 3:
        return SuperScraper.DATE_OF_BIRTH
    day, month, year = parts
    return f"{month}/{day}/{year}"


async def _combo(tab, super_scraper, field_id, value):
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        print(f"{super_scraper.OOPS} combobox '{field_id}' not found")
        return
    await field.click()
    await asyncio.sleep(0.3)
    # Type only a short prefix, then click the exact role="option". Typing the
    # full value makes some OneTrust vt-autocomplete builds type-ahead-complete
    # it AND keep the typed text, doubling the value ("United StatesUnited
    # States"); a short ambiguous prefix does not trigger that.
    await tab.keyboard.type_text(value[:5])
    await asyncio.sleep(1.4)
    option = await tab.find(
        xpath=f"//*[@role='option' and normalize-space()={value!r}]", raise_exc=False
    )
    if option:
        await option.click()
    else:
        await tab.keyboard.type_text(value[5:])
        await asyncio.sleep(0.8)
        await tab.keyboard.press(Key.ARROWDOWN)
        await asyncio.sleep(0.3)
        await tab.keyboard.press(Key.ENTER)
    await asyncio.sleep(0.5)
    current = await field.execute_script("return this.value")
    cur = current.get("result", {}).get("result", {}).get("value") if isinstance(current, dict) else current
    if cur and value.lower() not in str(cur).lower():
        print(f"{super_scraper.OOPS} combobox '{field_id}' value looks wrong: {cur!r}")


async def _pick(tab, super_scraper, label):
    opt = await tab.find(**{"aria-label": label}, raise_exc=False)
    if not opt:
        opt = await tab.find(
            xpath=f"//*[@role='option' and normalize-space()={label!r}]", raise_exc=False
        )
    if opt:
        await opt.click_using_js()
        await asyncio.sleep(0.4)
    else:
        print(f"{super_scraper.OOPS} option {label!r} not found")


async def submit_request(tab, right_label, tag, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(7)

    await _combo(tab, super_scraper, "countryDSARElement", "United States")
    await _combo(tab, super_scraper, "stateDSARElement", SuperScraper.STATE)
    city = await tab.find(id="cityDSARElement", raise_exc=False)
    if city:
        await city.type_text(SuperScraper.CITY)

    await _pick(tab, super_scraper, "Myself")
    await _pick(tab, super_scraper, right_label)
    await asyncio.sleep(1)

    for field_id, value in (
        ("firstNameDSARElement", SuperScraper.FIRST_NAME),
        ("lastNameDSARElement", SuperScraper.LAST_NAME),
        ("emailDSARElement", SuperScraper.EMAIL),
        ("dateOfBirthDSARElement", _dob_mm_dd_yyyy()),
    ):
        if not value:
            continue
        el = await tab.find(id=field_id, raise_exc=False)
        if el:
            await el.type_text(value)
            await asyncio.sleep(0.2)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    await asyncio.sleep(1)
    await tab.take_screenshot(
        path=f"resources/screenshots/idstrong_dry_run_{tag}.png", beyond_viewport=True
    )
    print(f"Screenshot saved to resources/screenshots/idstrong_dry_run_{tag}.png")
    print(f"'{right_label}' filled but NOT submitted — solve the reCAPTCHA manually, then Submit.")


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
        for right_label, tag in rights:
            await submit_request(tab, right_label, tag, super_scraper)


asyncio.run(main())
