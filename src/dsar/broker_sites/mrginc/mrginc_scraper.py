# mrginc.com — /do-not-sell-my-personal-information. Plain server-rendered
# form beneath a long CCPA rights-notice page. Checkboxes: do_not_sell_info
# (Opt-Out), delete_my_info (Delete, gated on REMOVE_INFORMATION),
# request_my_data (Access) — all selectable together in one submission
# (select-all-that-apply, not single-select). State is plain free text.
# The "CAPTCHA" is a simple, dynamically-generated arithmetic question
# ("What is 4 + 10?", regenerated on every page load) — genuinely
# solvable by parsing the two numbers and computing the sum, so this
# scraper solves it and (in live mode) can submit for real without any
# manual step.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.mrginc.com/do-not-sell-my-personal-information"

RIGHT_MAP = {
    "access": ["checkbox_request"],
    "opt_out_sale_share": ["checkbox"],
    "delete": ["checkbox_delete"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        fields = {
            "full_name": f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}",
            "email": SuperScraper.EMAIL,
            "address": SuperScraper.ADDRESS,
            "city": SuperScraper.CITY,
            "state": SuperScraper.STATE,
            "zip": SuperScraper.ZIP_CODE,
        }
        for field_name, value in fields.items():
            if not value:
                continue
            field = await tab.find(xpath=f"//input[@name='{field_name}']", raise_exc=False)
            if field:
                await field.type_text(value)
            else:
                print(f"{super_scraper.OOPS} field '{field_name}' not found")

        codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
        if not codes:
            print("No requested privacy rights apply to this form — nothing to do.")
            return
        checkbox_ids = [cb for code in codes for cb in RIGHT_MAP[code]]
        for checkbox_id in checkbox_ids:
            checkbox = await tab.find(id=checkbox_id, raise_exc=False)
            if checkbox:
                await checkbox.click()
            else:
                print(f"{super_scraper.OOPS} checkbox '{checkbox_id}' not found")

        page_text = await SuperScraper.page_text(tab)
        answer = SuperScraper.solve_math_captcha(page_text or "")
        if answer is not None:
            answer_field = await tab.find(xpath="//input[@placeholder='Your answer']", raise_exc=False)
            if answer_field:
                await answer_field.type_text(answer)
            else:
                print(f"{super_scraper.OOPS} math-captcha answer field not found")
        else:
            print(f"{super_scraper.OOPS} math-captcha question not found/parseable")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/mrginc_dry_run.png")
        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
            return

        submit_btn = await tab.find(text="Submit", raise_exc=False)
        if submit_btn:
            await submit_btn.click()
            await asyncio.sleep(2)
            print(f"Submitted request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        else:
            print(f"{super_scraper.OOPS} Submit button not found")


asyncio.run(main())
