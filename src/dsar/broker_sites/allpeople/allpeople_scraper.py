# allpeople.com — opt-out/removal only (no separate Access or Delete form).
# Step 1: fills email + agreement checkbox, then pauses for user to solve reCAPTCHA v2.
# Step 2 onward: user must search for their record in the browser and click "Remove",
# then confirm via the email link sent by the site.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://allpeople.com/removal"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

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

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit removal for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}"
                f" <{SuperScraper.EMAIL}>"
            )
            print("Pausing 5s for screenshot...")
            await asyncio.sleep(5)
            await SuperScraper.screenshot(tab, "resources/screenshots/allpeople_dry_run.png")
            return

        print(f"\nEmail and agreement filled for {SuperScraper.EMAIL}.")
        print("Solve the reCAPTCHA in the browser, then click 'Begin Removal Process'.")
        print("After the next page loads, search for your record and click 'Remove'.")
        print("Press Enter when done (after clicking Remove on your record)...")
        input()
        print("Check your email for a confirmation link to complete the removal.")


asyncio.run(main())
