# careerbuilder.com — server-rendered privacy request form, no captcha. One
# submission per request type: "access" (Access), "dns" (Do Not Sell/Share -> Opt-out)
# and "deletion" (Delete). Which of them run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). Relation defaults
# to "Other" since a generic data-subject request doesn't map to any of the
# job-seeker/employee-specific options. Address is a plain textarea (single
# free-text field, not split into street/city/state/zip).
#
# Page elements:
#   input#name                 Full name (first + last)
#   input#email                Email
#   textarea#address           Address
#   select#relation            Relation -> "other"
#   select#type                Request type -> "access" / "dns" / "deletion"
#   button#submitBtn           Submit
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://www.careerbuilder.com/privacy/"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "access",
    Right.RIGHT_TO_OPT_OUT: "dns",
    Right.RIGHT_TO_DELETE: "deletion",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, right, type_value, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(3)

    await super_scraper.input_text_field(tab=tab, xpath="//input[@id='name']", text=f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}", sleep=0.3)
    await super_scraper.input_text_field(tab=tab, xpath="//input[@id='email']", text=SuperScraper.EMAIL, sleep=0.3)
    await super_scraper.input_text_field(tab=tab, xpath="//textarea[@id='address']", text=SuperScraper.ADDRESS, sleep=0.3)

    await tab.execute_script(
        'var s = document.querySelector("select#relation"); s.value = "other"; s.dispatchEvent(new Event("change"));'
    )
    await tab.execute_script(
        f'var s = document.querySelector("select#type"); s.value = "{type_value}"; s.dispatchEvent(new Event("change"));'
    )

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        return

    await super_scraper.click_item_by_xpath(tab=tab, xpath="//button[@id='submitBtn']", sleep=2)
    await asyncio.sleep(2)
    print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()
    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, right, RIGHT_MAP[right], super_scraper)


asyncio.run(main())
