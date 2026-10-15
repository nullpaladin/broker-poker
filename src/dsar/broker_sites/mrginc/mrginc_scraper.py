# mrginc.com — /do-not-sell-my-personal-information. Plain server-rendered
# form beneath a long CCPA rights-notice page. Select-all-that-apply checkboxes, all
# submitted together in ONE submission. Which of them are checked is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). State is plain free text.
# The "CAPTCHA" is a simple, dynamically-generated arithmetic question
# ("What is 4 + 10?", regenerated on every page load) — solved with
# captcha_solutions_util.solve_math_captcha, so live mode needs no manual step.
#
# Page elements (keep this list current):
#   input[name=full_name]      Full name (first + last)
#   input[name=email]          Email
#   input[name=address] / [name=city] / [name=state] / [name=zip]   Address / City / State (free text) / Zip
#   #checkbox                  do_not_sell_info  "Opt-Out" (Do not sell)
#   #checkbox_delete           delete_my_info    "Delete"
#   #checkbox_request          request_my_data   "Access"
#   input[placeholder="Your answer"]   arithmetic CAPTCHA answer
#   "Submit" button            found by its text
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper
from src.dsar import captcha_solutions_util
from src.dsar import js_utils

from pydoll.browser.chromium import Chrome

URL = "https://www.mrginc.com/do-not-sell-my-personal-information"

OPT_OUT_CHECKBOX = "checkbox"  # do_not_sell_info
DELETE_CHECKBOX = "checkbox_delete"  # delete_my_info
ACCESS_CHECKBOX = "checkbox_request"  # request_my_data

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [ACCESS_CHECKBOX],
    Right.RIGHT_TO_OPT_OUT: [OPT_OUT_CHECKBOX],
    Right.RIGHT_TO_DELETE: [DELETE_CHECKBOX],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    checkbox_ids = [cb for right in rights for cb in RIGHT_MAP[right]]

    options = SuperScraper.build_chromium_options()

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

        for checkbox_id in checkbox_ids:
            checkbox = await tab.find(id=checkbox_id, raise_exc=False)
            if checkbox:
                await checkbox.click()
            else:
                print(f"{super_scraper.OOPS} checkbox '{checkbox_id}' not found")

        page_text = await js_utils.page_text(tab)
        answer = captcha_solutions_util.solve_math_captcha(page_text or "")
        if answer is not None:
            answer_field = await tab.find(xpath="//input[@placeholder='Your answer']", raise_exc=False)
            if answer_field:
                await answer_field.type_text(answer)
            else:
                print(f"{super_scraper.OOPS} math-captcha answer field not found")
        else:
            print(f"{super_scraper.OOPS} math-captcha question not found/parseable")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run_" + "_".join(r.value for r in rights))
        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit {'/'.join(r.name for r in rights)} for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
            return

        submit_btn = await tab.find(text="Submit", raise_exc=False)
        if submit_btn:
            await submit_btn.click()
            await asyncio.sleep(2)
            print(f"Submitted {'/'.join(r.name for r in rights)} for {SuperScraper.EMAIL} — confirm in the browser.")
        else:
            print(f"{super_scraper.OOPS} Submit button not found")


asyncio.run(main())
