# trueblueanalytics.org — "Your Privacy Choices" form is rendered directly
# on trueblueanalytics.org/dont-sell (an Optacy.com-managed widget, no
# iframe). First Name/Last Name/Email are standard inputs. "I am a"
# (id="requester_type") answered "other" (options: customer/employee/
# job_applicant/vendor/other). Country (id="country", native select keyed
# by 2-letter code) — selecting it reveals a State select
# (id="state", native select keyed by FULL state name, not abbreviation),
# which in turn reveals the "Your Rights" checkbox group (stable ids):
# data_categories_request (Access), do_not_sell (Opt-out),
# erase_my_information (Delete, gated on REMOVE_INFORMATION),
# send_me_a_copy_of_information (portability) checked unconditionally;
# correct_my_information and appeal_a_decision skipped (no concrete
# inaccuracy/decision to reference); "other" (free-text) skipped. Visible
# (non-invisible) reCAPTCHA v2 — **CAPTCHA solution required**.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://trueblueanalytics.org/dont-sell"

RIGHT_IDS = [
    "data_categories_request",
    "do_not_sell",
    "send_me_a_copy_of_information",
]
DELETE_RIGHT_ID = "erase_my_information"


async def _select_native_option(select_element, option_value):
    await select_element.execute_script(
        "for (var i=0;i<this.options.length;i++){"
        f"  if(this.options[i].value==={option_value!r}){{ this.selectedIndex=i; }}"
        "}"
        "this.dispatchEvent(new Event('change', {bubbles:true}));"
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,3000")

    right_ids = list(RIGHT_IDS)
    if SuperScraper.REMOVE_INFORMATION:
        right_ids.append(DELETE_RIGHT_ID)

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
            await _select_native_option(requester_type_select, "other")
        else:
            print(f"{super_scraper.OOPS} 'I am a' select not found")

        country_select = await tab.find(id="country", raise_exc=False)
        if country_select:
            await _select_native_option(country_select, "US")
            await asyncio.sleep(1.5)
        else:
            print(f"{super_scraper.OOPS} Country select not found")

        # Only revealed in the DOM after Country is set above.
        state_select = await tab.find(id="state", raise_exc=False)
        if state_select:
            await _select_native_option(state_select, SuperScraper.STATE)
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
        await tab.take_screenshot(path="resources/screenshots/trueblueanalytics_dry_run.png")
        print("Screenshot saved to resources/screenshots/trueblueanalytics_dry_run.png")
        print(
            "\nRequest filled but NOT submitted — a visible reCAPTCHA v2 checkbox requires "
            "a manual solve before submitting."
        )


asyncio.run(main())
