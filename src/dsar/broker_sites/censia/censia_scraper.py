# censia.com — Google Form ("Remove My Data"). All fields are short-answer
# text inputs; Google Forms wires them up with aria-labelledby pointing at
# the question heading rather than a direct aria-label, so each is targeted
# by an xpath scoped to its role="listitem" container instead. Rights are
# a single multi-select checkbox group (checkboxes DO carry aria-label
# directly): "Access my PI" (Access), "Do not sell my PI" (Opt-out) and a third
# option left labeled "Option 3" by Censia itself (a form-authoring mistake, not
# something this scraper can fix), positioned as the third of a standard
# Access/Opt-Out/Delete triad and therefore treated as Delete (unverified).
# Which rights are ticked is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# No CAPTCHA.
#
# Page elements:
#   listitem "First Name" / "Last Name" / "Phone Number" / "Email Address" /
#   "City" / "State" / "Zip Code" / "Country"   Short-answer text inputs
#   checkbox[aria-label=<entry>]   Rights checkboxes (see RIGHT_MAP)
#   "Submit" button
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://docs.google.com/forms/d/1VhF33VAQG4AmUqBWf7e3m8fw17h9ek64EtQXnuuBQcA/viewform?edit_requested=true"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Access my PI"],
    Right.RIGHT_TO_OPT_OUT: ["Do not sell my PI"],
    Right.RIGHT_TO_DELETE: ["Option 3"],
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
        await asyncio.sleep(4)

        fields = [
            ("First Name", SuperScraper.FIRST_NAME),
            ("Last Name", SuperScraper.LAST_NAME),
            ("Phone Number", SuperScraper.PHONE_NUMBER),
            ("Email Address", SuperScraper.EMAIL),
            ("City", SuperScraper.CITY),
            ("State", SuperScraper.STATE),
            ("Zip Code", SuperScraper.ZIP_CODE),
            ("Country", "United States"),
        ]
        for label, value in fields:
            field = await tab.find(
                xpath=f"//div[@role='listitem'][.//span[contains(text(),'{label}')]]//input",
                raise_exc=False,
            )
            if field:
                await field.type_text(value)
                await asyncio.sleep(0.2)

        checkboxes = [entry for right in rights for entry in RIGHT_MAP[right]]
        for label in checkboxes:
            box = await tab.find(**{"aria-label": label}, raise_exc=False)
            if box:
                await box.click()
                await asyncio.sleep(0.2)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit {[r.name for r in rights]} for {SuperScraper.EMAIL}")
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "dry_run")
            return

        await super_scraper.click_item_by_text(tab=tab, text="Submit", sleep=2)
        await asyncio.sleep(2)
        print(f"Submitted {[r.name for r in rights]} for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())
