# kochava.com — Opt-Out only by Mobile Advertising ID (IDFA/GAID).
# No Access or Delete form — opt-out is the only right available.
# Requires ADVERTISING_ID in UUID format (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx).
# reCAPTCHA v2 checkbox requires manual solve; submit button is disabled
# until the reCAPTCHA callback enables it.
# honeypot field must be left empty.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://www.kochava.com/opt-out-do-not-sell-request-process/"


async def main():
    options = ChromiumOptions()
    options.binary_location = "/snap/bin/chromium"
    options.add_argument("--no-sandbox")
    super_scraper = SuperScraper()

    if not SuperScraper.ADVERTISING_ID:
        print(f"{super_scraper.OOPS} ADVERTISING_ID not set — kochava requires a Mobile Ad ID (IDFA/GAID)")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        maid_field = await tab.find(tag_name="input", name="maid", raise_exc=False)
        if not maid_field:
            print(f"{super_scraper.OOPS} MAID field not found")
            return
        await maid_field.type_text(SuperScraper.ADVERTISING_ID)

        # Leave honeypot empty (do not interact with it)

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit opt-out for MAID={SuperScraper.ADVERTISING_ID}"
            )
            await tab.take_screenshot("kochava_dry_run.png")
            print("Screenshot saved to kochava_dry_run.png")
            return

        print(f"\nMAID field filled: {SuperScraper.ADVERTISING_ID}")
        print("Solve the reCAPTCHA checkbox in the browser — it will enable the Submit button.")
        print("Press Enter after clicking Submit and the confirmation appears...")
        input()

        source = await tab.page_source
        if any(w in source.lower() for w in ("received", "submitted", "thank", "success")):
            print(f"Submitted opt-out for MAID={SuperScraper.ADVERTISING_ID}")
        else:
            print(f"{super_scraper.OOPS} Confirmation unclear — verify in browser")


asyncio.run(main())
