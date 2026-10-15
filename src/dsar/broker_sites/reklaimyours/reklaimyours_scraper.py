# reklaimyours.com (Reklaim) — exercises Do Not Sell/Share, Access, Delete (gated only by
# SuperScraper.rights_to_exercise(RIGHT_MAP)).
# React form, one submission per right type. No CAPTCHA. Radio buttons are custom
# role="radio" <button> elements — use click_using_js(). Jurisdiction set to "other"
# (Minnesota not listed in jurisdiction dropdown).
#
# Page elements:
#   #email                     Email
#   #name                      Name (first + last)
#   #requestType-access        "Access" request-type radio
#   #requestType-do_not_sell   "Do not sell" request-type radio
#   #requestType-delete        "Delete" request-type radio
#   text "Submit Request"      Submit button
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.reklaimyou.com/optout"

# (radio button id, screenshot label)
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("requestType-access", "access")],
    Right.RIGHT_TO_OPT_OUT: [("requestType-do_not_sell", "optout")],
    Right.RIGHT_TO_DELETE: [("requestType-delete", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


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
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
        print(
            f"DRY RUN: would submit '{label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        return

    submit = await tab.find(text="Submit Request", raise_exc=False)
    if submit:
        await submit.click()
    await asyncio.sleep(4)

    print(f"Submitted '{label}' for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    requests = [entry for right in rights for entry in RIGHT_MAP[right]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for radio_id, label in requests:
            await submit_request(tab, radio_id, label, super_scraper)


asyncio.run(main())
