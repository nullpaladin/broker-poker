# peoplefinders.com — two separate URLs for two separate rights:
#
# Opt-Out/Delete (https://www.peoplefinders.com/opt-out): the ENTIRE page
# is covered by a Cloudflare "Please complete the security challenge"
# interstitial with no page content of any kind reachable behind it in an
# automated session — not just a gate on the final submit step. Per this
# repo's policy, a full-page block like this is left unchecked/
# undocumented-further rather than attempted, unlike a CAPTCHA that only
# gates a submit button.
#
# Access (https://www.peoplefinders.com/request-my-info): this page loads
# normally. "View Account Information" requires an existing PeopleFinders
# account login (skipped — not applicable to a generic non-member
# consumer). "Request My Information" (Reports & Records) opens a 3-step
# wizard (Request My Info > Verify Identity > Confirmation). Step 1 is
# just a relationship radio (`firstRadioOption`="my own information" /
# `secondRadioOption`="on another person's behalf") gated by a reCAPTCHA
# v2 checkbox before "Continue" advances — so the real identity-
# verification form on step 2 is never reached in an automated session.
# This scraper selects "my own information" and stops there.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.peoplefinders.com/request-my-info"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        request_btn = await tab.find(text="Request My Information", raise_exc=False)
        if not request_btn:
            print(f"{super_scraper.OOPS} 'Request My Information' button not found")
            return
        await request_btn.click()
        await asyncio.sleep(2)

        # The real <input id="firstRadioOption"> is visually hidden behind
        # custom radio styling — native .click() raises ElementNotVisible,
        # and a JS checked=true set doesn't update the visual state either.
        # Clicking the label text itself (via click_using_js) does.
        own_info_label = await tab.find(text="my own information", raise_exc=False)
        if own_info_label:
            await own_info_label.click_using_js()
        else:
            print(f"{super_scraper.OOPS} 'my own information' label not found")

        await tab.execute_script("window.scrollTo(0, 0);")
        await asyncio.sleep(1)
        await tab.take_screenshot(path="resources/screenshots/peoplefinders_dry_run.png")
        print("Screenshot saved to resources/screenshots/peoplefinders_dry_run.png")
        print(
            "\n'My own information' selected but the wizard cannot proceed further — a "
            "reCAPTCHA v2 checkbox gates the 'Continue' button before the actual identity-"
            "verification form (step 2) is reachable, and requires a manual solve.\n"
            "Separately, the Opt-Out/Delete page (peoplefinders.com/opt-out) is entirely "
            "behind a full-page Cloudflare challenge with no reachable content — not "
            "attempted here."
        )


asyncio.run(main())
