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
# Rights the form exposes: Access only; whether it runs is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP).
#
# Page elements (keep this list current):
#   "Request My Information" button (text)   opens the 3-step wizard
#   #firstRadioOption  "my own information" radio (clicked via its label text, click_using_js)
#   #secondRadioOption "on another person's behalf" radio (not used)
#   reCAPTCHA v2 checkbox gating "Continue" — manual solve
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils

URL = "https://www.peoplefinders.com/request-my-info"

RIGHT_MAP = {Right.RIGHT_TO_ACCESS: "Request My Information"}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (A wizard that stops at a reCAPTCHA before any field; no rights chooser or fields to assert.)


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

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

        await js_utils.js_eval(tab, "window.scrollTo(0, 0); return true;")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run_access")
        print(
            "\n'My own information' selected but the wizard cannot proceed further — a "
            "reCAPTCHA v2 checkbox gates the 'Continue' button before the actual identity-"
            "verification form (step 2) is reachable, and requires a manual solve.\n"
            "Separately, the Opt-Out/Delete page (peoplefinders.com/opt-out) is entirely "
            "behind a full-page Cloudflare challenge with no reachable content — not "
            "attempted here."
        )


asyncio.run(main())
