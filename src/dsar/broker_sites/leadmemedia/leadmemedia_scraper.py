# leadmemedia.com — policy.leadmemedia.com/States/privacyrequestform.html.
# A single server-rendered form with plain, stable field ids/names and a
# select-all-that-apply checkbox group (name=DeleteInfo/NotSell/Access/
# Correct/Limit/NoTarget/ThirdParty) — one submission covers every right
# checked. Correct/Limit/NoTarget/ThirdParty are not automated. Which rights
# run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP). State is a plain free-text field, not
# a select — the full state name is accepted (no format hint/maxlength
# constraint found). reCAPTCHA v2 present — **CAPTCHA solution required**.
#
# Page elements:
#   #email / #first-name / #last-name   Email, First / Last name
#   #address / #city / #state / #zip    Address fields (state is free text)
#   checkbox name=Access      Access
#   checkbox name=NotSell     Do not sell
#   checkbox name=DeleteInfo  Delete
#   (also present, unused: Correct / Limit / NoTarget / ThirdParty checkboxes)
#   reCAPTCHA v2 checkbox
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://policy.leadmemedia.com/States/privacyrequestform.html"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Access"],
    Right.RIGHT_TO_OPT_OUT: ["NotSell"],
    Right.RIGHT_TO_DELETE: ["DeleteInfo"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    super_scraper = SuperScraper()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        fields = {
            "email": SuperScraper.EMAIL,
            "first-name": SuperScraper.FIRST_NAME,
            "last-name": SuperScraper.LAST_NAME,
            "address": SuperScraper.ADDRESS,
            "city": SuperScraper.CITY,
            "state": SuperScraper.STATE,
            "zip": SuperScraper.ZIP_CODE,
        }
        for field_id, value in fields.items():
            if not value:
                continue
            field = await tab.find(id=field_id, raise_exc=False)
            if field:
                await field.type_text(value)
            else:
                print(f"{super_scraper.OOPS} field '{field_id}' not found")

        checkbox_names = [entry for right in rights for entry in RIGHT_MAP[right]]
        for name in checkbox_names:
            checkbox = await tab.find(xpath=f"//input[@name='{name}']", raise_exc=False)
            if checkbox:
                await checkbox.click()
            else:
                print(f"{super_scraper.OOPS} checkbox '{name}' not found")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run")
        print(
            "\nForm filled but NOT submitted — a reCAPTCHA v2 checkbox is present and "
            "requires a manual solve before submitting."
        )


asyncio.run(main())
