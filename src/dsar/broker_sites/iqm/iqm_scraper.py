# iqm.com — OneTrust DSAR webform (privacyportal-de.onetrust.com/webform).
#   countryDSARElement  autocomplete combobox -> United States
#   subjectTypesDSARElement  "I am a (an)": Customer / Other -> "Customer"
#   stateDSARElement  autocomplete combobox (renders after Country) -> STATE
#   requestTypesDSARElement  role="option" group, treated as single-select
#       (one submission per right): "Info Request" (Access), "Do Not Sell My
#       Information" (Opt-out), "Data Deletion" (Delete).
#   firstNameDSARElement / lastNameDSARElement / emailDSARElement
#   requestDetailsDSARElement left blank.
# Which rights run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# reCAPTCHA gates submit — filled to that point.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.constants import Key

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = (
    "https://privacyportal-de.onetrust.com/webform/"
    "7436a756-393f-458a-a582-dca7d0d14e78/6e117877-3171-4edd-b9ef-4b42732bcace"
)

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("Info Request", "access")],
    Right.RIGHT_TO_OPT_OUT: [("Do Not Sell My Information", "do_not_sell")],
    Right.RIGHT_TO_DELETE: [("Data Deletion", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list

FIELD_XPATHS = {
    "Country": "//*[@id='countryDSARElement']",
    "State": "//*[@id='stateDSARElement']",
    "First name": "//*[@id='firstNameDSARElement']",
    "Last name": "//*[@id='lastNameDSARElement']",
    "Email": "//*[@id='emailDSARElement']",
}


async def _combo(tab, super_scraper, field_id, value):
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        print(f"{super_scraper.OOPS} combobox '{field_id}' not found")
        return
    await field.click()
    await asyncio.sleep(0.3)
    # This OneTrust vt-autocomplete build type-ahead-completes AND keeps the
    # typed text, doubling any fully-typed value ("United StatesUnited States").
    # Set the value once via the native setter + input event so the option list
    # filters to the single match, then commit that match with the keyboard;
    # finally hard-correct the field if it still came out doubled/wrong.
    await field.execute_script(
        "var s=Object.getOwnPropertyDescriptor(Object.getPrototypeOf(this),'value').set;"
        f"s.call(this,{value!r});"
        "this.dispatchEvent(new Event('input',{bubbles:true}));"
    )
    await asyncio.sleep(1.4)
    option = await tab.find(
        xpath=f"//*[@role='option' and normalize-space()={value!r}]", raise_exc=False
    )
    if option:
        await option.click()
    else:
        await tab.keyboard.press(Key.ENTER)
    await asyncio.sleep(0.5)
    current = await field.execute_script("return this.value")
    cur = current.get("result", {}).get("result", {}).get("value") if isinstance(current, dict) else current
    if str(cur or "").strip().lower() != value.lower():
        await field.execute_script(
            "var s=Object.getOwnPropertyDescriptor(Object.getPrototypeOf(this),'value').set;"
            f"s.call(this,{value!r});"
            "this.dispatchEvent(new Event('input',{bubbles:true}));"
            "this.dispatchEvent(new Event('change',{bubbles:true}));"
            "this.dispatchEvent(new Event('blur',{bubbles:true}));"
        )
        await asyncio.sleep(0.3)


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
    await _pick(tab, super_scraper, "Customer")
    await _combo(tab, super_scraper, "stateDSARElement", SuperScraper.STATE)
    await _pick(tab, super_scraper, right_label)
    await asyncio.sleep(1)

    for field_id, value in (
        ("firstNameDSARElement", SuperScraper.FIRST_NAME),
        ("lastNameDSARElement", SuperScraper.LAST_NAME),
        ("emailDSARElement", SuperScraper.EMAIL),
    ):
        el = await tab.find(id=field_id, raise_exc=False)
        if el:
            await el.type_text(value)
            await asyncio.sleep(0.2)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{tag}")
    print(f"'{right_label}' filled but NOT submitted — solve the reCAPTCHA manually, then Submit.")


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            for right_label, tag in RIGHT_MAP[right]:
                await submit_request(tab, right_label, tag, super_scraper)


asyncio.run(main())
