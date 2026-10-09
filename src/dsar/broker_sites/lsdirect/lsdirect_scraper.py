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
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://lsdirect.com/my-personal-information/"


async def _select_by_text(select_element, text):
    await select_element.execute_script(
        "for (var i=0;i<this.options.length;i++){"
        f"  if(this.options[i].text.trim()==={text!r}){{ this.selectedIndex=i; }}"
        "}"
        "this.dispatchEvent(new Event('change', {bubbles:true}));"
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,2400")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        for cb_id in ("form-field-6c47d8-0", "form-field-6c47d8-1"):
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
            await _select_by_text(state, SuperScraper.STATE)

        await asyncio.sleep(1)
        await tab.take_screenshot(path="resources/screenshots/lsdirect_dry_run.png", beyond_viewport=True)
        print("Screenshot saved to resources/screenshots/lsdirect_dry_run.png")

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit opt-out + access for {SuperScraper.EMAIL}")
            return

        submit = await tab.find(xpath="//form//button[@type='submit']", raise_exc=False)
        if submit:
            await submit.click()
            await asyncio.sleep(4)
            print(f"Submitted opt-out + access for {SuperScraper.EMAIL}")


asyncio.run(main())
