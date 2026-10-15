# fetcher.ai — https://app.fetcher.ai/opt-out . Small React/Ant-Design form,
# opt-out only: "If we have a record of you in our database we will process your
# request for removal once you hit submit." Every other right is email-only
# (support@fetcher.ai — privacy@fetcher.ai does not exist) per README.
# Fields: #first_name, #last_name, #email, then a reCAPTCHA v2 checkbox and
# Submit — filled to that point and left for a manual solve.
# **CAPTCHA solution required**
#
# Page elements:
#   #first_name / #last_name / #email   First / Last name / Email
#   reCAPTCHA v2 checkbox, Submit button  (left for the user)
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://app.fetcher.ai/opt-out"

RIGHT_MAP = {Right.RIGHT_TO_OPT_OUT: "removal"}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        fields = {
            "first_name": SuperScraper.FIRST_NAME,
            "last_name": SuperScraper.LAST_NAME,
            "email": SuperScraper.EMAIL,
        }
        for field_id, val in fields.items():
            if not val:
                continue
            el = await tab.find(id=field_id, raise_exc=False)
            if el:
                await el.type_text(val)
                await asyncio.sleep(0.2)
            else:
                print(f"{super_scraper.OOPS} field '{field_id}' not found")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run")
        print(
            "Opt-out request filled but NOT submitted — solve the reCAPTCHA v2 "
            "checkbox manually, then click Submit."
        )


asyncio.run(main())
