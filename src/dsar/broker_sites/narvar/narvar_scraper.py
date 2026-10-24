# narvar.com — Custom OneTrust portal (narvar.my.onetrust.com).
# Subject type: "End consumer". Request types are all visible from the start and are
# multi-select: every selected right goes in a single submission. Request types the form
# offers: Access, Portability, Rectification, Restriction, Deletion. Which run is decided
# ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP). Rectification (right to correct) is
# NOT automated (not in RIGHT_MAP) — list it as None in a PAGE_RIGHTS inventory if a
# health check is added. Only email required (no name/address fields). reCAPTCHA v2 —
# manual solve.
#
# Page elements (keep this list current):
#   aria-label "End consumer"      subject type button
#   aria-label <request>           request-type buttons: Access / Portability / Rectification /
#                                  Restriction / Deletion (see RIGHT_MAP)
#   #emailDSARElement              Email
#   #formField78DSARElement        "Order number or Email address" (optional, left blank)
#   #requestDetailsDSARElement     "Additional Information" (optional textarea, left blank)
#   aria-label "Click to submit form"   Submit button
#   reCAPTCHA v2 checkbox          manual solve
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://narvar.my.onetrust.com/webform/04b3731f-2a9a-42ce-bd6b-106d4b4ec3bf/a7c944bf-3cec-4f00-9dc5-dea5bf2b6f4f"

SUBJECT_END_CONSUMER = "End consumer"  # subject type button
EMAIL_ID = "emailDSARElement"  # Email
SUBMIT_LABEL = "Click to submit form"  # Submit button

# Right -> list of request-type buttons (aria-labels) the form offers for it.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Access", "Portability"],
    Right.RIGHT_TO_OPT_OUT: ["Restriction"],
    Right.RIGHT_TO_DELETE: ["Deletion"],
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
    requests = [entry for right in rights for entry in RIGHT_MAP[right]]
    names = "/".join(right.name for right in rights)

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(7)

        # Subject type: End consumer
        consumer = await tab.find(**{"aria-label": SUBJECT_END_CONSUMER}, raise_exc=False)
        if consumer:
            await consumer.click_using_js()
            await asyncio.sleep(0.5)
        else:
            print(f"{super_scraper.OOPS} 'End consumer' subject button not found")

        # Request types
        for req in requests:
            btn = await tab.find(**{"aria-label": req}, raise_exc=False)
            if btn:
                await btn.click_using_js()
                await asyncio.sleep(0.3)
            else:
                print(f"{super_scraper.OOPS} Request button '{req}' not found")

        # Email
        email = await tab.find(id=EMAIL_ID, raise_exc=False)
        if email:
            await email.type_text(SuperScraper.EMAIL)

        time.sleep(0.5)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit {names} for {SuperScraper.EMAIL}")
            submit_btn = await tab.find(**{"aria-label": SUBMIT_LABEL}, raise_exc=False)
            if submit_btn:
                await submit_btn.scroll_into_view()
            await asyncio.sleep(2)
            await SuperScraper.screenshot(tab, "dry_run_" + "_".join(r.value for r in rights))
            return

        print(
            f"\nForm filled. Solve the reCAPTCHA, then click Submit. "
            f"Press Enter after the confirmation page appears..."
        )
        input()

        print(f"Submitted {names} for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())
