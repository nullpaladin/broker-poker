# outlogic.io — /opt-out-form/. Nearly identical privacy-notice text and
# structure to matchbookdata.com elsewhere in this repo (evidently a
# related product/vendor family) — identifies consumers only by mobile
# Device ID (Advertising or Installation ID) and email. The page has TWO
# separate Gravity Forms: `gform_2` is the actual opt-out form (Device
# ID/Email — targeted here); its third field, labeled "Name"
# (input_2_3), is a honeypot (height:0, autocomplete="new-password"),
# deliberately left blank. `gform_3` is an unrelated
# "Contact Us" form (Email/Question/Phone) that happens to share generic
# `input_N` field-name numbering with other Gravity Forms on the page —
# don't confuse the two by field name alone, always resolve via
# `gform_2`'s own field ids (input_2_1/2_2/2_3). No request-type selector
# — a single, unconditional opt-out submission (no separate Access/Delete
# control). A Cookiebot consent banner covers the page on first load and
# must be dismissed first. No CAPTCHA observed on this form specifically
# (the g-recaptcha field on the page belongs to the separate Contact Us
# form).
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://outlogic.io/opt-out-form/"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        deny_btn = await tab.find(id="CybotCookiebotDialogBodyButtonDecline", raise_exc=False)
        if deny_btn:
            await deny_btn.click()
            await asyncio.sleep(1)

        device_id_field = await tab.find(id="input_2_1", raise_exc=False)
        if device_id_field and SuperScraper.ADVERTISING_ID:
            await device_id_field.type_text(SuperScraper.ADVERTISING_ID)
        else:
            print(f"{super_scraper.OOPS} device ID field not found or ADVERTISING_ID not set")

        email_field = await tab.find(id="input_2_2", raise_exc=False)
        if email_field:
            await email_field.type_text(SuperScraper.EMAIL)

        # input_2_3 ("Name") is a honeypot despite its label: height:0 and
        # autocomplete="new-password" (a classic anti-bot trap) — left
        # deliberately BLANK, same pattern as leadloft.com/lsmapps.com/
        # m1data.com elsewhere in this repo.

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/outlogic_dry_run.png")
        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit opt-out request for {SuperScraper.EMAIL} (device ID: {SuperScraper.ADVERTISING_ID})")
            return

        submit_btn = await tab.find(id="gform_submit_button_2", raise_exc=False)
        if submit_btn:
            await submit_btn.click()
            await asyncio.sleep(2)
            print(f"Submitted opt-out request for {SuperScraper.EMAIL}")
        else:
            print(f"{super_scraper.OOPS} Submit button not found")


asyncio.run(main())
