# allantgroup.com — OneTrust CDN DSAR webform
# (privacyportal-cdn.onetrust.com/dsarwebform).
#   requestTypesDSARElement  role="option" group, single-select (one submission
#       per right): "Access My Information" + "Do Not Sell My Information"
#       unconditionally; "Delete My Information" gated on REMOVE_INFORMATION.
#   emailDSARElement / firstNameDSARElement / lastNameDSARElement
#   addressDSARElement / cityDSARElement / formField17DSARElement (state) /
#       zipDSARElement / phoneNumberDSARElement
#   dateOfBirthDSARElement  date picker (MM/DD/YYYY, from .env DD/MM/YYYY)
#   Middle name / Suffix / Apartment (formField21/22/23) left blank.
#   An "ACKNOWLEDGEMENT" checkbox ("I confirm that the information ... is
#       accurate and that I am the individual submitting the request") is
#       checked.
#   Optional State-ID photo upload is left blank.
# reCAPTCHA gates submit — filled to that point.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = (
    "https://privacyportal-cdn.onetrust.com/dsarwebform/"
    "cbbe21b6-d675-445f-9c24-f625c01dafb3/b0160307-96f2-4e7b-9cd8-c70b09b0a76b.html"
)

RIGHT_MAP = {
    "access": [("Access My Information", "access")],
    "opt_out_sale_share": [("Do Not Sell My Information", "do_not_sell")],
    "delete": [("Delete My Information", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


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

    await _pick(tab, super_scraper, right_label)

    for field_id, value in (
        ("emailDSARElement", SuperScraper.EMAIL),
        ("firstNameDSARElement", SuperScraper.FIRST_NAME),
        ("lastNameDSARElement", SuperScraper.LAST_NAME),
        ("addressDSARElement", SuperScraper.ADDRESS),
        ("cityDSARElement", SuperScraper.CITY),
        ("zipDSARElement", SuperScraper.ZIP_CODE),
        ("phoneNumberDSARElement", SuperScraper.PHONE_NUMBER),
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

    state_field = await tab.find(id="formField17DSARElement", raise_exc=False)
    if state_field:
        await state_field.type_text(SuperScraper.STATE)

    ack = await tab.find(
        **{"aria-label": "By submitting this form, I confirm that the information I have provided is accurate and that I am the individual submitting the request."},
        raise_exc=False,
    )
    if not ack:
        ack = await tab.find(
            xpath="//*[@role='checkbox'] | //input[@type='checkbox']", raise_exc=False
        )
    if ack:
        await ack.click_using_js()
    else:
        print(f"{super_scraper.OOPS} acknowledgement checkbox not found")

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/allantgroup_dry_run_{tag}.png", beyond_viewport=True)
    print(f"'{right_label}' filled but NOT submitted — solve the reCAPTCHA manually, then Submit.")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    rights = [entry for code in codes for entry in RIGHT_MAP[code]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right_label, tag in rights:
            await submit_request(tab, right_label, tag, super_scraper)


asyncio.run(main())
