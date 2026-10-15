# lsdirect.com — /my-personal-information/ Elementor Pro form, server-rendered,
# AJAX POST in place. "I would like to request the following action:" is a
# checkbox group (multi-select, one combined submission):
#   form-field-6c47d8-0  "Opt out of sharing"           -> Opt-Out
#   form-field-6c47d8-1  "Request information about ..." -> Access
# Both are checked. Fields (Elementor random `form-field-<hex>` ids):
#   form-field-12c652 first, form-field-d0b8e9 last, form-field-239f51 address1,
#   form-field-5c0abd address2, form-field-ed3995 city,
#   form-field-f184b1 <select> state (full names), form-field-be2796 zip,
#   form-field-be43c6 email
# No CAPTCHA observed.
#
# Page elements:
#   form-field-6c47d8-0   "Opt out of sharing" checkbox
#   form-field-6c47d8-1   "Request information about ..." checkbox (access)
#   form-field-12c652 / form-field-d0b8e9   First / Last name
#   form-field-239f51 / form-field-5c0abd   Address line 1 / line 2
#   form-field-ed3995     City
#   form-field-f184b1     State <select> (full names)
#   form-field-be2796     ZIP
#   form-field-be43c6     Email
#   form submit button    (//form//button[@type='submit'])
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://lsdirect.com/my-personal-information/"

CHECK_OPT_OUT = "form-field-6c47d8-0"  # "Opt out of sharing"
CHECK_ACCESS = "form-field-6c47d8-1"  # "Request information about ..."

# Right -> the "I would like to request the following action" checkbox id (one combined submission).
RIGHT_MAP = {
    Right.RIGHT_TO_OPT_OUT: CHECK_OPT_OUT,
    Right.RIGHT_TO_ACCESS: CHECK_ACCESS,
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


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
        await tab.go_to(URL)
        await asyncio.sleep(6)

        for cb_id in (RIGHT_MAP[right] for right in rights):
            cb = await tab.find(id=cb_id, raise_exc=False)
            if cb:
                await cb.click()
                await asyncio.sleep(0.2)
            else:
                print(f"{super_scraper.OOPS} checkbox '{cb_id}' not found")

        fields = {
            "form-field-12c652": SuperScraper.FIRST_NAME,
            "form-field-d0b8e9": SuperScraper.LAST_NAME,
            "form-field-239f51": SuperScraper.ADDRESS,
            "form-field-5c0abd": SuperScraper.ADDRESS_LINE_TWO,
            "form-field-ed3995": SuperScraper.CITY,
            "form-field-be2796": SuperScraper.ZIP_CODE,
            "form-field-be43c6": SuperScraper.EMAIL,
        }
        for field_id, val in fields.items():
            if not val:
                continue
            el = await tab.find(id=field_id, raise_exc=False)
            if el:
                await el.type_text(val)
                await asyncio.sleep(0.15)
            else:
                print(f"{super_scraper.OOPS} field '{field_id}' not found")

        state = await tab.find(id="form-field-f184b1", raise_exc=False)
        if state:
            await js_utils.select_native_option(state, text=SuperScraper.STATE)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run")
        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit {[r.name for r in rights]} for {SuperScraper.EMAIL}")
            return

        submit = await tab.find(xpath="//form//button[@type='submit']", raise_exc=False)
        if submit:
            await submit.click()
            await asyncio.sleep(4)
            print(f"Submitted {[r.name for r in rights]} for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())
