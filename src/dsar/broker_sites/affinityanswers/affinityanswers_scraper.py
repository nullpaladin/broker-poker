# affinityanswers.com — exercises Access, Correct, Opt-Out of Sale,
# Opt-Out of Targeted Advertising, and Delete (gated on REMOVE_INFORMATION).
# Single Gravity Forms POST form. Residency select uses full state name.
# reCAPTCHA v3 is invisible and auto-resolves in the browser.
# input_13 is a honeypot field — must be left empty.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://www.affinityanswers.com/your-privacy-choices/"

# US rights checkboxes — always exercised
ALWAYS_CHECK = [
    "choice_11_5_1",  # access
    "choice_11_5_3",  # correct
    "choice_11_5_4",  # opt-out of sale
    "choice_11_5_5",  # opt-out of targeted advertising
]
DELETE_CHECKBOX_ID = "choice_11_5_2"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        # Residency select — full state name
        residency_select = await tab.find(tag_name="select", name="input_4", raise_exc=False)
        if residency_select:
            state_opt = await residency_select.find(tag_name="option", value=SuperScraper.STATE, raise_exc=False)
            if state_opt:
                await state_opt.click()
            else:
                print(f"{super_scraper.OOPS} State '{SuperScraper.STATE}' not in residency dropdown")
        time.sleep(0.5)

        # Email field
        email_field = await tab.find(tag_name="input", name="input_3", raise_exc=False)
        if email_field:
            await email_field.type_text(SuperScraper.EMAIL)

        # US rights checkboxes
        checkbox_ids = list(ALWAYS_CHECK)
        if SuperScraper.REMOVE_INFORMATION:
            checkbox_ids.append(DELETE_CHECKBOX_ID)

        for cb_id in checkbox_ids:
            cb = await tab.find(id=cb_id, raise_exc=False)
            if cb:
                await cb.click()
            time.sleep(0.3)

        # Leave honeypot input_13 untouched

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit for "
                f"{SuperScraper.EMAIL} / state={SuperScraper.STATE}"
            )
            submit_btn = await tab.find(id="gform_submit_button_11", raise_exc=False)
            if submit_btn:
                await submit_btn.scroll_into_view()
            await asyncio.sleep(2)
            await tab.take_screenshot("resources/screenshots/affinityanswers_dry_run.png")
            print("Screenshot saved to resources/screenshots/affinityanswers_dry_run.png")
            return

        submit_btn = await tab.find(id="gform_submit_button_11", raise_exc=False)
        if not submit_btn:
            print(f"{super_scraper.OOPS} Submit button not found")
            return
        await submit_btn.click()
        await asyncio.sleep(5)

        source = await tab.page_source
        if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
            print(f"Submitted DSAR for {SuperScraper.EMAIL}")
        else:
            print(f"{super_scraper.OOPS} Confirmation unclear — verify in browser")


asyncio.run(main())
