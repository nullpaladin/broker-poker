# allantgroup.com — OneTrust CDN DSAR webform
# (privacyportal-cdn.onetrust.com/dsarwebform).
#   requestTypesDSARElement  role="option" group, single-select (one submission
#       per right): "Access My Information", "Do Not Sell My Information",
#       "Delete My Information"; which run is decided only by rights_to_exercise.
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
from pydoll.constants import Key

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = (
    "https://privacyportal-cdn.onetrust.com/dsarwebform/"
    "cbbe21b6-d675-445f-9c24-f625c01dafb3/b0160307-96f2-4e7b-9cd8-c70b09b0a76b.html"
)

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("Access My Information", "access")],
    Right.RIGHT_TO_OPT_OUT: [("Do Not Sell My Information", "do_not_sell")],
    Right.RIGHT_TO_DELETE: [("Delete My Information", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every option in the request-type group, as displayed -> the Right it maps to.
PAGE_RIGHTS = {
    "Access My Information": Right.RIGHT_TO_ACCESS,
    "Do Not Sell My Information": Right.RIGHT_TO_OPT_OUT,
    "Delete My Information": Right.RIGHT_TO_DELETE,
}
RIGHTS_OPTIONS_CSS = "#requestTypesDSARElement [role='option']"

FIELD_XPATHS = {
    "Email": "//*[@id='emailDSARElement']",
    "First name": "//*[@id='firstNameDSARElement']",
    "Last name": "//*[@id='lastNameDSARElement']",
    "Address": "//*[@id='addressDSARElement']",
    "City": "//*[@id='cityDSARElement']",
    "State": "//*[@id='formField17DSARElement']",
    "Zip": "//*[@id='zipDSARElement']",
    "Phone": "//*[@id='phoneNumberDSARElement']",
    "Date of birth": "//*[@id='dateOfBirthDSARElement']",
}


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
    cur = await js_utils.js_eval(field, "return this.value")
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


async def submit_request(tab, right, right_label, tag, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(7)

    if SuperScraper.HEALTH_CHECK:
        offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
        SuperScraper.audit_rights(offered, PAGE_RIGHTS)

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

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{right.value}_{tag}")
    print(f"'{right.name}' ('{right_label}') filled but NOT submitted — solve the reCAPTCHA manually, then Submit.")


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
            for right_label, tag in RIGHT_MAP[right]:
                await submit_request(tab, right, right_label, tag, super_scraper)


asyncio.run(main())
