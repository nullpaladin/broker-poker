# truedata.co — TrueData "Access / Delete Request" form at
# info-prod.truedata.co/access-delete-request.
# Server-rendered React form. Request type is a set of independent checkboxes
# (optOutRequest / deleteRequest / accessRequest), NOT a single-select — one
# combined submission covers every checked right. optOutRequest and
# deleteRequest are checked by default on page load; this scraper forces
# accessRequest + optOutRequest on and leaves deleteRequest on ONLY when
# REMOVE_INFORMATION is set.
# Country/State are native <select>s; State is disabled until Country changes.
# "name" is a single full-name field. MAID (ADVERTISING_ID) and the OS/CTV
# identifier fields are optional and left blank (no real device id on file).
# reCAPTCHA v2 gates submission — form filled and left for a manual solve.
# **CAPTCHA solution required**
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://info-prod.truedata.co/access-delete-request"


async def _set_checkbox(tab, element_id, desired):
    el = await tab.find(id=element_id, raise_exc=False)
    if not el:
        print(f"checkbox #{element_id} not found")
        return
    await el.execute_script(
        f"if (this.checked !== {str(desired).lower()}) this.click();"
    )


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
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        await _set_checkbox(tab, "accessRequest", True)
        await _set_checkbox(tab, "optOutRequest", True)
        await _set_checkbox(tab, "deleteRequest", SuperScraper.wants("delete"))
        await asyncio.sleep(0.5)

        # "Access" reveals the category sub-checkboxes — ask for all categories.
        cats = await tab.find(id="categoriesInfo", raise_exc=False)
        if cats:
            await SuperScraper.js_check(cats)

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
        await SuperScraper.screenshot(tab, "resources/screenshots/truedata_dry_run.png")
        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit access+opt-out"
                f"{'+delete' if SuperScraper.wants("delete") else ''} for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
            )
            return

        print("\nForm filled. Solve the reCAPTCHA in the browser, click Submit, then press Enter...")
        input()

        source = await tab.page_source
        if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
            print(f"Submitted for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        else:
            print(f"{super_scraper.OOPS} Confirmation unclear — verify in browser")


asyncio.run(main())
