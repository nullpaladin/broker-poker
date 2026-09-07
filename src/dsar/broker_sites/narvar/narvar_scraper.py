# narvar.com — Custom OneTrust portal (narvar.my.onetrust.com).
# Subject type: "End consumer". Request types are all visible from the start.
# Exercises Access, Portability, Rectification, Restriction unconditionally;
# Deletion gated on REMOVE_INFORMATION. All selected in a single submission.
# Only email required (no name/address fields). reCAPTCHA v2 — manual solve.
# formField78DSARElement = "Order number or Email address" (optional, left blank).
# requestDetailsDSARElement = "Additional Information" (optional textarea).
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://narvar.my.onetrust.com/webform/04b3731f-2a9a-42ce-bd6b-106d4b4ec3bf/a7c944bf-3cec-4f00-9dc5-dea5bf2b6f4f"

RIGHT_MAP = {
    "access": ["Access"],
    "portability": ["Portability"],
    "correct": ["Rectification"],
    "opt_out_sale_share": ["Restriction"],
    "delete": ["Deletion"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(7)

        # Subject type: End consumer
        consumer = await tab.find(**{"aria-label": "End consumer"}, raise_exc=False)
        if consumer:
            await consumer.click_using_js()
            await asyncio.sleep(0.5)
        else:
            print(f"{super_scraper.OOPS} 'End consumer' subject button not found")

        # Request types
        codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
        if not codes:
            print("No requested privacy rights apply to this form — nothing to do.")
            return
        requests = [entry for code in codes for entry in RIGHT_MAP[code]]

        for req in requests:
            btn = await tab.find(**{"aria-label": req}, raise_exc=False)
            if btn:
                await btn.click_using_js()
                await asyncio.sleep(0.3)
            else:
                print(f"{super_scraper.OOPS} Request button '{req}' not found")

        # Email
        email = await tab.find(id="emailDSARElement", raise_exc=False)
        if email:
            await email.type_text(SuperScraper.EMAIL)

        time.sleep(0.5)

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit Access/Portability/Rectification/Restriction"
                f"{'/Deletion' if SuperScraper.REMOVE_INFORMATION else ''} "
                f"for {SuperScraper.EMAIL}"
            )
            submit_btn = await tab.find(**{"aria-label": "Click to submit form"}, raise_exc=False)
            if submit_btn:
                await submit_btn.scroll_into_view()
            await asyncio.sleep(2)
            await SuperScraper.screenshot(tab, "resources/screenshots/narvar_dry_run.png")
            print("Screenshot: resources/screenshots/narvar_dry_run.png")
            return

        print(
            f"\nForm filled. Solve the reCAPTCHA, then click Submit. "
            f"Press Enter after the confirmation page appears..."
        )
        input()

        source = await tab.page_source
        if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
            print(f"Submitted DSAR for {SuperScraper.EMAIL}")
        else:
            print(f"{super_scraper.OOPS} Confirmation unclear — verify in browser")


asyncio.run(main())
