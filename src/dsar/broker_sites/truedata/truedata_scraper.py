# truedata.co — TrueData "Access / Delete Request" form at
# info-prod.truedata.co/access-delete-request.
# Server-rendered React form. Request type is a set of independent checkboxes
# (optOutRequest / deleteRequest / accessRequest), NOT a single-select — one
# combined submission covers every checked right. optOutRequest and
# deleteRequest are checked by default on page load; this scraper sets each of the
# three checkboxes on/off according to SuperScraper.rights_to_exercise(RIGHT_MAP).
# Country/State are native <select>s; State is disabled until Country changes.
# "name" is a single full-name field. MAID (ADVERTISING_ID) and the OS/CTV
# identifier fields are optional and left blank (no real device id on file).
# reCAPTCHA v2 gates submission — form filled and left for a manual solve.
# **CAPTCHA solution required**
#
# Page elements:
#   #accessRequest / #optOutRequest / #deleteRequest   request-type checkboxes (see RIGHT_MAP)
#   #categoriesInfo     all-categories checkbox revealed by Access
#   #country            Country <select> -> "United States"
#   #state              State <select> (disabled until Country changes)
#   #formBasicEmail     Email
#   #name               Full name (single field)
#   [name=address1] / [name=city] / [name=zip]   Address / City / Zip
#   #phone              Phone
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://info-prod.truedata.co/access-delete-request"

# Right -> request-type checkbox id.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "accessRequest",
    Right.RIGHT_TO_OPT_OUT: "optOutRequest",
    Right.RIGHT_TO_DELETE: "deleteRequest",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def _set_checkbox(tab, element_id, desired):
    el = await tab.find(id=element_id, raise_exc=False)
    if not el:
        print(f"checkbox #{element_id} not found")
        return
    await js_utils.js_check(el, desired)


async def _select_native(tab, element_id, match_text):
    """Select an <option> in a React-controlled <select> by its visible text,
    using the native value setter so React's onChange actually fires."""
    el = await tab.find(id=element_id, raise_exc=False)
    if not el:
        print(f"select #{element_id} not found")
        return
    await el.execute_script(
        """
        const wanted = %r.trim().toLowerCase();
        const opt = Array.from(this.options).find(
            o => o.textContent.trim().toLowerCase() === wanted
        );
        if (opt) {
            const setter = Object.getOwnPropertyDescriptor(
                window.HTMLSelectElement.prototype, 'value').set;
            setter.call(this, opt.value);
            this.dispatchEvent(new Event('input', {bubbles: true}));
            this.dispatchEvent(new Event('change', {bubbles: true}));
        }
        """
        % match_text
    )


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        for right, checkbox_id in RIGHT_MAP.items():
            await _set_checkbox(tab, checkbox_id, right in rights)
        await asyncio.sleep(0.5)

        # "Access" reveals the category sub-checkboxes — ask for all categories.
        if Right.RIGHT_TO_ACCESS in rights:
            cats = await tab.find(id="categoriesInfo", raise_exc=False)
            if cats:
                await js_utils.js_check(cats)

        await _select_native(tab, "country", "United States")
        await asyncio.sleep(1)

        state = await tab.find(id="state", raise_exc=False)
        if state:
            await state.execute_script("this.disabled = false;")
        await _select_native(tab, "state", SuperScraper.STATE)

        for xpath, value in {
            "//input[@id='formBasicEmail']": SuperScraper.EMAIL,
            "//input[@id='name']": f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}",
            "//input[@name='address1']": SuperScraper.ADDRESS,
            "//input[@name='city']": SuperScraper.CITY,
            "//input[@name='zip']": SuperScraper.ZIP_CODE,
            "//input[@id='phone']": SuperScraper.PHONE_NUMBER,
        }.items():
            await super_scraper.input_text_field(tab=tab, xpath=xpath, text=value, sleep=0.3)

        time.sleep(0.5)
        await SuperScraper.screenshot(tab, "dry_run")
        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit {[r.name for r in rights]} for {SuperScraper.EMAIL}")
            return

        print("\nForm filled. Solve the reCAPTCHA in the browser, click Submit, then press Enter...")
        input()

        print(f"Submitted {[r.name for r in rights]} for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())
