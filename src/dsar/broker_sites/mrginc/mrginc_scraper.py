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
import re

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.mrginc.com/do-not-sell-my-personal-information"


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

        checkbox_ids = ["checkbox", "checkbox_request"]
        if SuperScraper.REMOVE_INFORMATION:
            checkbox_ids.append("checkbox_delete")
        for checkbox_id in checkbox_ids:
            checkbox = await tab.find(id=checkbox_id, raise_exc=False)
            if checkbox:
                await checkbox.click()
            else:
                print(f"{super_scraper.OOPS} checkbox '{checkbox_id}' not found")

        page_text = await tab.execute_script("return document.body.innerText")
        if isinstance(page_text, dict):
            page_text = page_text.get("result", {}).get("result", {}).get("value", "")
        match = re.search(r"What is (\d+)\s*\+\s*(\d+)\?", page_text or "")
        if match:
            answer = str(int(match.group(1)) + int(match.group(2)))
            answer_field = await tab.find(xpath="//input[@placeholder='Your answer']", raise_exc=False)
            if answer_field:
                await answer_field.type_text(answer)
            else:
                print(f"{super_scraper.OOPS} math-captcha answer field not found")
        else:
            print(f"{super_scraper.OOPS} math-captcha question not found/parseable")

        await asyncio.sleep(1)
        await tab.take_screenshot(path="resources/screenshots/mrginc_dry_run.png")
        print("Screenshot saved to resources/screenshots/mrginc_dry_run.png")

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
