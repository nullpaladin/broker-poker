# spycloud.com — Osano DSAR portal (my.datasubject.com/169m4FTnIOxju2VXg/28523).
# Step 1: click request type card (pydoll find by text + click).
# Step 2: fill email (id="email"), first name (id="given-name"),
#   last name (id="family-name"), requestor type select (id="requestor-type",
#   value="CUSTOMER" = "Individual"). Standard HTML inputs — element.type_text works.
# Cloudflare Turnstile present — manual solve required in live mode.
# Minnesota auto-detected from IP; no location selection needed.
# One submission per right (separate page navigation each time).
# Exercises: Summarize/Access, Do Not Sell, Correct, Opt-Out of Advertising,
#   Opt-Out of Profiling, Delete (gated on REMOVE_INFORMATION).
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://my.datasubject.com/169m4FTnIOxju2VXg/28523"

ALWAYS_RIGHTS = [
    "Summarize my personal information",
    "Do Not Sell or Share to a Third Party",
    "Correct my personal information",
    "Don't use my personal information for advertising",
    "Opt Out of Profiling / Automated Decision-Making",
]
DELETE_RIGHT = "Delete my personal information"


async def _fill_step2(tab, super_scraper):
    """Fill step 2 personal info fields. Returns True on success."""
    email_field = await tab.find(id="email", raise_exc=False)
    if not email_field:
        print(f"{super_scraper.OOPS} email field not found")
        return False

    await email_field.click()
    await email_field.type_text(SuperScraper.EMAIL)

    fname = await tab.find(id="given-name", raise_exc=False)
    if fname:
        await fname.click()
        await fname.type_text(SuperScraper.FIRST_NAME)

    lname = await tab.find(id="family-name", raise_exc=False)
    if lname:
        await lname.click()
        await lname.type_text(SuperScraper.LAST_NAME)

    # Requestor type: Individual (CUSTOMER)
    req_select = await tab.find(tag_name="select", id="requestor-type", raise_exc=False)
    if req_select:
        customer_opt = await req_select.find(tag_name="option", value="CUSTOMER", raise_exc=False)
        if customer_opt:
            await customer_opt.click()

    time.sleep(0.5)
    return True


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    rights = list(ALWAYS_RIGHTS)
    if SuperScraper.REMOVE_INFORMATION:
        rights.append(DELETE_RIGHT)

    async with Chrome(options=options) as browser:
        tab = await browser.start()

        for right in rights:
            await tab.go_to(URL)
            await asyncio.sleep(7)

            # Step 1: click request type card
            card = await tab.find(text=right, raise_exc=False)
            if not card:
                print(f"{super_scraper.OOPS} Card not found: '{right}'")
                continue
            await card.click()
            await asyncio.sleep(3)

            # Step 2: fill personal info
            if not await _fill_step2(tab, super_scraper):
                continue

            if SuperScraper.DRY_RUN:
                await asyncio.sleep(1)
                safe_name = right.replace(" ", "_").replace("/", "_")[:30]
                await SuperScraper.screenshot(tab, f"resources/screenshots/spycloud_dry_run_{safe_name}.png")
                print(
                    f"DRY RUN: would submit spycloud '{right}' for "
                    f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
                )
                continue

            print(
                f"\n'{right}' form filled. Solve the Cloudflare Turnstile, "
                "then click Submit. Press Enter after the confirmation page loads..."
            )
            input()

            src = await tab.page_source
            if any(w in src.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
                print(f"Submitted '{right}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
            else:
                print(f"{super_scraper.OOPS} Confirmation unclear for '{right}' — verify in browser")


asyncio.run(main())
