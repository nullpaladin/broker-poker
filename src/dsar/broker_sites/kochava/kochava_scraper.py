# kochava.com — Opt-Out only by Mobile Advertising ID (IDFA/GAID).
# No Access or Delete form — opt-out is the only right available. Whether it runs is
# decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# Requires ADVERTISING_ID in UUID format (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx).
# reCAPTCHA v2 checkbox requires manual solve; submit button is disabled
# until the reCAPTCHA callback enables it.
# honeypot field must be left empty.
#
# Page elements:
#   input[name=maid]   Mobile Advertising ID
#   reCAPTCHA v2 checkbox -> enables the Submit button
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.kochava.com/opt-out-do-not-sell-request-process/"

RIGHT_MAP = {Right.RIGHT_TO_OPT_OUT: "opt-out"}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    super_scraper = SuperScraper()
    if not SuperScraper.rights_to_exercise(RIGHT_MAP):
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    options = SuperScraper.build_chromium_options()

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
            await SuperScraper.screenshot(tab, "dry_run")
            return

        print(f"\nMAID field filled: {SuperScraper.ADVERTISING_ID}")
        print("Solve the reCAPTCHA checkbox in the browser — it will enable the Submit button.")
        print("Press Enter after clicking Submit and the confirmation appears...")
        input()

        print(f"Submitted 'RIGHT_TO_OPT_OUT' for MAID={SuperScraper.ADVERTISING_ID} — confirm in the browser.")


asyncio.run(main())
