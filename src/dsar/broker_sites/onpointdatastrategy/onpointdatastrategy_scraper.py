# onpointdatastrategy.com — OnPoint Data Strategy "opt-out" request, a 2-page
# Gravity Forms form (form id 1) at onpointdatastrategy.com/opt-out/.
# Page 1 holds every field; "Submit Request" (gform_next_button_1_8) advances to
# page 2 (reCAPTCHA + final submit).
# GF advanced-name field: input_1.3 = first, input_1.6 = last (1.2 prefix, 1.4
# middle, 1.8 suffix left blank). GF address field: input_4.1 street, 4.3 city,
# 4.4 state (a TEXT input, not a select), 4.5 zip, 4.6 country <select>.
# input_3 = email, input_6 = phone (optional). input_5 = a required "Request
# Type" <select> (enhanced-UI / chosen,
# so the native value is set via the value property + change event): options
# "Opt-Out Only", "Do Not Sell My Data Only", "Request Information Only",
# "Opt Out & Request Information", "Remove me from your database" — this scraper
# picks "Remove me from your database" when REMOVE_INFORMATION is set, else
# "Opt Out & Request Information".
# The page-1 "Next" advances cleanly once every required field (incl. the
# free-text State) is set. NOTE: the placeholder `.env` email jdoe@example.com
# is rejected by the form as an invalid domain — a real address is needed for a
# live run. reCAPTCHA v2 on page 2 needs a manual solve.
# **CAPTCHA solution required**
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://onpointdatastrategy.com/opt-out/"


async def _select_native(tab, element_id, match_text):
    el = await tab.find(id=element_id, raise_exc=False)
    if not el:
        return
    await el.execute_script(
        f"const w={match_text.lower()!r};"
        "const o=[...this.options].find(x=>x.text.trim().toLowerCase()===w"
        " || x.value.toLowerCase()===w);"
        "if(o){const s=Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set;"
        "s.call(this,o.value);"
        "this.dispatchEvent(new Event('input',{bubbles:true}));"
        "this.dispatchEvent(new Event('change',{bubbles:true}));}"
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    request_type = (
        "Remove me from your database"
        if SuperScraper.REMOVE_INFORMATION
        else "Opt Out & Request Information"
    )

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        for xpath, value in {
            "//input[@id='input_1_1_3']": SuperScraper.FIRST_NAME,
            "//input[@id='input_1_1_6']": SuperScraper.LAST_NAME,
            "//input[@id='input_1_3']": SuperScraper.EMAIL,
            "//input[@id='input_1_4_1']": SuperScraper.ADDRESS,
            "//input[@id='input_1_4_3']": SuperScraper.CITY,
            "//input[@id='input_1_4_4']": SuperScraper.STATE,
            "//input[@id='input_1_4_5']": SuperScraper.ZIP_CODE,
            "//input[@id='input_1_6']": SuperScraper.PHONE_NUMBER,
        }.items():
            await super_scraper.input_text_field(tab=tab, xpath=xpath, text=value, sleep=0.2)

        await _select_native(tab, "input_1_4_6", "United States")      # address: country
        await _select_native(tab, "input_1_5", request_type)           # request type

        await asyncio.sleep(0.5)
        next_btn = await tab.find(id="gform_next_button_1_8", raise_exc=False)
        if next_btn:
            await next_btn.click()
            await asyncio.sleep(4)

        page2_visible = await tab.execute_script(
            "const p=document.getElementById('gform_page_1_2');"
            "return !!p && getComputedStyle(p).display!=='none';"
        )
        advanced = bool(page2_visible["result"]["result"]["value"])
        await tab.take_screenshot("resources/screenshots/onpointdatastrategy_dry_run.png")
        print("Screenshot saved to resources/screenshots/onpointdatastrategy_dry_run.png")

        if not advanced:
            print(
                f"{super_scraper.OOPS} Page 1 filled (request type: '{request_type}') but 'Next' "
                f"did not advance — Gravity Forms anti-spam under automation. Click Next manually, "
                f"then solve the page-2 reCAPTCHA and submit."
            )
            return

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: page 1 filled and advanced (request type: '{request_type}') for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>. "
                f"Page 2 has a reCAPTCHA + final submit."
            )
            return

        print("\nPage 2 reached. Solve the reCAPTCHA, click the final Submit, then press Enter...")
        input()


asyncio.run(main())
