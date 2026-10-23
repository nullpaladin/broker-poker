# allpeople.com — opt-out/removal only (no separate Access or Delete form).
# Step 1: fills email + agreement checkbox, then pauses for user to solve reCAPTCHA v2.
# Step 2 onward: user must search for their record in the browser and click "Remove",
# then confirm via the email link sent by the site.
# Mapped to RIGHT_TO_OPT_OUT (the removal flow); decided only by SuperScraper.rights_to_exercise.
#
# Page elements:
#   #email                 Email
#   #agreement-checkbox    Agreement checkbox
#   reCAPTCHA v2           Manual solve
#   "Begin Removal Process" button, then a record search and a "Remove" button on the next page
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://allpeople.com/removal"

RIGHT_MAP = {
    Right.RIGHT_TO_OPT_OUT: "removal",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list

EMAIL_XPATH = "//*[@id='email']"


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(4)

        await tab.execute_script(
            f"document.getElementById('email').value = {__import__('json').dumps(SuperScraper.EMAIL)};"
            "document.getElementById('email').dispatchEvent(new Event('input', {bubbles: true}));"
        )
        await tab.execute_script(
            "var cb = document.getElementById('agreement-checkbox');"
            "cb.checked = true;"
            "cb.dispatchEvent(new Event('change', {bubbles: true}));"
        )

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, {"Email": EMAIL_XPATH})

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit '{Right.RIGHT_TO_OPT_OUT.name}' (removal) for {SuperScraper.EMAIL}"
            )
            print("Pausing 5s for screenshot...")
            await asyncio.sleep(5)
            await SuperScraper.screenshot(tab, "dry_run_opt_out")
            return

        print(f"\nEmail and agreement filled for {SuperScraper.EMAIL}.")
        print("Solve the reCAPTCHA in the browser, then click 'Begin Removal Process'.")
        print("After the next page loads, search for your record and click 'Remove'.")
        print("Press Enter when done (after clicking Remove on your record)...")
        input()
        print("Check your email for a confirmation link to complete the removal.")


asyncio.run(main())
