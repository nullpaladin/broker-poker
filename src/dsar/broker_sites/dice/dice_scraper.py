# dice.com — /about/ccpa#ccpa-form-anchor . Server-rendered form
# (id="form-dice-ccpa", posts to a DHI Group forwarder).
#
# The "Please indicate whether you wish to" radio (name="description") is
# single-select, so exercising more than one right needs one submission each.
# This page is heavy (reCAPTCHA Enterprise) and a second full reload inside one
# browser session reliably hangs pydoll's load-event wait, so the scraper does
# ONE pass per run:
#   REMOVE_INFORMATION off -> "radio-description-access" (Access)
#   REMOVE_INFORMATION on  -> "radio-description-delete" (Delete)
# To also submit the Opt-Out variant, re-run after selecting
# "radio-description-optout" (it is the same form, one field).
#
# Fields: name (id "name"), email (id "email"). reCAPTCHA Enterprise gates the
# submit — filled to that point.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://www.dice.com/about/ccpa#ccpa-form-anchor"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    if SuperScraper.wants("delete"):
        radio_id, tag = "radio-description-delete", "delete"
    else:
        radio_id, tag = "radio-description-access", "access"

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        try:
            await tab.go_to(URL)
        except Exception as exc:
            print(f"(dice: go_to reported {exc!r} — continuing once DOM is ready)")
        await asyncio.sleep(8)

        radio = await tab.find(id=radio_id, raise_exc=False)
        if radio:
            await radio.click()
            await asyncio.sleep(0.3)
        else:
            print(f"{super_scraper.OOPS} radio '{radio_id}' not found")

        name = await tab.find(xpath="//form[@id='form-dice-ccpa']//input[@id='name']", raise_exc=False)
        if name:
            await name.type_text(f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}".strip())
        email = await tab.find(xpath="//form[@id='form-dice-ccpa']//input[@id='email']", raise_exc=False)
        if email:
            await email.type_text(SuperScraper.EMAIL)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/dice_dry_run_{tag}.png", beyond_viewport=True)
        print(
            f"'{tag}' request filled but NOT submitted — solve the reCAPTCHA manually, then "
            "Submit. Re-run with a different 'description' radio for the other rights."
        )


asyncio.run(main())
