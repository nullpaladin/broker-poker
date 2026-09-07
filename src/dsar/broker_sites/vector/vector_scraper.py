# vector.co — Vector "opt-out" form at vector.co/opt-out.
# Tiny server-rendered form wired to HubSpot (data-hs-do-not-collect): a single
# "name" field, "email", and a free-text "purpose" field ("What action would
# you like us to take on your data?"). No request-type picker and no CAPTCHA
# observed — one submission. The purpose text states the rights being
# exercised (deletion included only when REMOVE_INFORMATION is set).
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://www.vector.co/opt-out"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    purpose = (
        "I am a resident exercising my privacy rights: please opt me out of the "
        "sale/sharing of my personal information and of targeted advertising, and "
        "provide me access to the personal information you hold about me"
    )
    if SuperScraper.REMOVE_INFORMATION:
        purpose += ", and delete all personal information you hold about me"
    purpose += "."

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(4)

        await super_scraper.input_text_field(
            tab=tab, xpath="//input[@name='name']",
            text=f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}", sleep=0.3,
        )
        await super_scraper.input_text_field(
            tab=tab, xpath="//input[@name='email']", text=SuperScraper.EMAIL, sleep=0.3,
        )
        await super_scraper.input_text_field(
            tab=tab, xpath="//input[@name='purpose']", text=purpose, sleep=0.3,
        )

        time.sleep(0.5)
        submit = await tab.find(xpath="//form[@id='opt-out-form']//button[@type='submit']", raise_exc=False)
        if submit:
            await submit.scroll_into_view()
        await SuperScraper.screenshot(tab, "resources/screenshots/vector_dry_run.png")
        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit opt-out for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
            )
            return

        if submit:
            await submit.click()
            await asyncio.sleep(3)
        source = await tab.page_source
        if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
            print(f"Submitted opt-out for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        else:
            print(f"{super_scraper.OOPS} Confirmation unclear — verify in browser")


asyncio.run(main())
