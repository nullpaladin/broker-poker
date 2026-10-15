# trueblueanalytics.org — "Your Privacy Choices" form is rendered directly
# on trueblueanalytics.org/dont-sell (an Optacy.com-managed widget, no
# iframe). First Name/Last Name/Email are standard inputs. "I am a"
# (id="requester_type") answered "other" (options: customer/employee/
# job_applicant/vendor/other). Country (id="country", native select keyed
# by 2-letter code) — selecting it reveals a State select
# (id="state", native select keyed by FULL state name, not abbreviation),
# which in turn reveals the "Your Rights" checkbox group (stable ids):
# data_categories_request (Access), send_me_a_copy_of_information (Access),
# do_not_sell (Opt-out), erase_my_information (Delete) — only the ones chosen by
# SuperScraper.rights_to_exercise(RIGHT_MAP) are ticked, in one combined submission;
# correct_my_information and appeal_a_decision skipped (no concrete
# inaccuracy/decision to reference); "other" (free-text) skipped. Visible
# (non-invisible) reCAPTCHA v2 — **CAPTCHA solution required**.
#
# Page elements:
#   #first_name / #last_name / #email   First / Last name, Email
#   #requester_type                     "I am a" <select> -> "other"
#   #country                            Country <select> -> "US"
#   #state                              State <select> (full state name; revealed after Country)
#   #data_categories_request, #send_me_a_copy_of_information, #do_not_sell,
#   #erase_my_information               "Your Rights" checkboxes (revealed after State)
import asyncio

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://trueblueanalytics.org/dont-sell"

# Right -> "Your Rights" checkbox id(s).
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["data_categories_request", "send_me_a_copy_of_information"],
    Right.RIGHT_TO_OPT_OUT: ["do_not_sell"],
    Right.RIGHT_TO_DELETE: ["erase_my_information"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    right_ids = [entry for right in rights for entry in RIGHT_MAP[right]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        fields = {
            "first_name": SuperScraper.FIRST_NAME,
            "last_name": SuperScraper.LAST_NAME,
            "email": SuperScraper.EMAIL,
        }
        for field_id, value in fields.items():
            field = await tab.find(id=field_id, raise_exc=False)
            if field:
                await field.type_text(value)
            else:
                print(f"{super_scraper.OOPS} field '{field_id}' not found")

        requester_type_select = await tab.find(id="requester_type", raise_exc=False)
        if requester_type_select:
            await js_utils.select_native_option(requester_type_select, value="other")
        else:
            print(f"{super_scraper.OOPS} 'I am a' select not found")

        country_select = await tab.find(id="country", raise_exc=False)
        if country_select:
            await js_utils.select_native_option(country_select, value="US")
            await asyncio.sleep(1.5)
        else:
            print(f"{super_scraper.OOPS} Country select not found")

        # Only revealed in the DOM after Country is set above.
        state_select = await tab.find(id="state", raise_exc=False)
        if state_select:
            await js_utils.select_native_option(state_select, value=SuperScraper.STATE)
            await asyncio.sleep(1.5)
        else:
            print(f"{super_scraper.OOPS} State select not found")

        # The "Your Rights" checkboxes are only revealed after State is set above.
        for right_id in right_ids:
            checkbox = await tab.find(id=right_id, raise_exc=False)
            if checkbox:
                await checkbox.click()
            else:
                print(f"{super_scraper.OOPS} right checkbox '{right_id}' not found")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run")
        print(
            "\nRequest filled but NOT submitted — a visible reCAPTCHA v2 checkbox requires "
            "a manual solve before submitting."
        )


asyncio.run(main())
