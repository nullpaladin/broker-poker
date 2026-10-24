# spycloud.com — Osano DSAR portal (my.datasubject.com/169m4FTnIOxju2VXg/28523).
# Step 1: click request type card (pydoll find by text + click).
# Step 2: fill email (id="email"), first name (id="given-name"),
#   last name (id="family-name"), requestor type select (id="requestor-type",
#   value="CUSTOMER" = "Individual"). Standard HTML inputs — element.type_text works.
# Cloudflare Turnstile present — manual solve required in live mode.
# Minnesota auto-detected from IP; no location selection needed.
# One submission per right (separate page navigation each time).
# Request-type cards (see RIGHT_MAP): Summarize/Access; Do Not Sell + Opt-Out of
#   Advertising + Opt-Out of Profiling (all RIGHT_TO_OPT_OUT); Delete. "Correct my
#   personal information" is on the page but not automated (PAGE_RIGHTS: None).
#   Which run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# Page elements:
#   #email / #given-name / #family-name   Email / First name / Last name
#   select#requestor-type                 Requestor type -> option value CUSTOMER ("Individual")
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://my.datasubject.com/169m4FTnIOxju2VXg/28523"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Summarize my personal information"],
    Right.RIGHT_TO_OPT_OUT: [
        "Do Not Sell or Share to a Third Party",
        "Don't use my personal information for advertising",
        "Opt Out of Profiling / Automated Decision-Making",
    ],
    Right.RIGHT_TO_DELETE: ["Delete my personal information"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every request-type card on the page -> Right (None = deliberately not automated).
PAGE_RIGHTS = {
    "Summarize my personal information": Right.RIGHT_TO_ACCESS,
    "Correct my personal information": None,
    "Do Not Sell or Share to a Third Party": Right.RIGHT_TO_OPT_OUT,
    "Don't use my personal information for advertising": Right.RIGHT_TO_OPT_OUT,
    "Opt Out of Profiling / Automated Decision-Making": Right.RIGHT_TO_OPT_OUT,
    "Delete my personal information": Right.RIGHT_TO_DELETE,
}


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
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    requests = [(right, card_text) for right in rights for card_text in RIGHT_MAP[right]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()

        for right, card_text in requests:
            await tab.go_to(URL)
            await asyncio.sleep(7)

            # Step 1: click request type card
            card = await tab.find(text=card_text, raise_exc=False)
            if not card:
                print(f"{super_scraper.OOPS} Card not found: '{card_text}'")
                continue
            await card.click()
            await asyncio.sleep(3)

            # Step 2: fill personal info
            if not await _fill_step2(tab, super_scraper):
                continue

            if SuperScraper.DRY_RUN:
                await asyncio.sleep(1)
                safe_name = card_text.replace(" ", "_").replace("/", "_")[:30]
                await SuperScraper.screenshot(tab, f"dry_run_{safe_name}")
                print(
                    f"DRY RUN: would submit '{right.name}' ('{card_text}') for "
                    f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
                )
                continue

            print(
                f"\n'{card_text}' form filled. Solve the Cloudflare Turnstile, "
                "then click Submit. Press Enter after the confirmation page loads..."
            )
            input()

            print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())
