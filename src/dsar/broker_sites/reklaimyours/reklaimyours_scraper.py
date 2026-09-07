# reklaimyours.com (Reklaim) — exercises Do Not Sell/Share, Access, Delete (gated).
# React form, one submission per right type. No CAPTCHA. Radio buttons are custom
# role="radio" <button> elements — use click_using_js(). Jurisdiction set to "other"
# (Minnesota not listed in jurisdiction dropdown).
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://www.reklaimyou.com/optout"

# (radio button id, screenshot label)
REQUESTS = [
    ("requestType-do_not_sell", "optout"),
    ("requestType-access",      "access"),
]
DELETE_REQUEST = ("requestType-delete", "delete")


async def submit_request(tab, radio_id, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    email = await tab.find(id="email", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    name_field = await tab.find(id="name", raise_exc=False)
    if name_field:
        await name_field.type_text(f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")

    radio_btn = await tab.find(id=radio_id, raise_exc=False)
    if radio_btn:
        await radio_btn.click_using_js()
    else:
        print(f"{super_scraper.OOPS} Radio button '{radio_id}' not found")
        return

    time.sleep(0.5)

    if SuperScraper.DRY_RUN:
        await SuperScraper.screenshot(tab, f"resources/screenshots/reklaimyours_dry_run_{label}.png")
        print(
            f"DRY RUN: would submit '{label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        return

    submit = await tab.find(text="Submit Request", raise_exc=False)
    if submit:
        await submit.click()
    await asyncio.sleep(4)

    source = await tab.page_source
    if any(w in source.lower() for w in ("success", "thank", "confirm", "received", "submitted")):
        print(f"Submitted '{label}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{label}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    requests = list(REQUESTS)
    if SuperScraper.REMOVE_INFORMATION:
        requests.append(DELETE_REQUEST)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for radio_id, label in requests:
            await submit_request(tab, radio_id, label, super_scraper)


asyncio.run(main())
