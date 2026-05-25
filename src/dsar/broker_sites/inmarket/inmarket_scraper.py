# inmarket.com — DataGrail Privacy Request Center.
# URL pre-fills country (United States) and state (MN) via locationCode param.
# Request types: Access, Opt-Out (sale/share + limit sensitive), Update Inaccuracies, Transfer — always.
# Deletion gated on REMOVE_INFORMATION.
# Each type: click "Start X Request" card, fill form, select relationship "Other" via role=option,
#   click "Review Request", then "Submit Request" in live mode.
# No CAPTCHA. Two-step email verification after submission.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = "https://preferences.inmarket.com/?locationCode=US-MN"

ALWAYS_REQUESTS = [
    ("Start Access Request", "access"),
    ("Start Request to Opt Out or Limit Use of Sensitive Personal Information", "optout"),
    ("Start Update Inaccuracies Request", "update"),
    ("Start Transfer Request", "transfer"),
]
DELETE_REQUEST = ("Start Deletion Request", "delete")


async def _select_relationship(tab):
    # Options: Business Contact(1), Customer(2), Employee(3), Former Employee(4),
    #          Job Applicant(5), Other(6) — press ArrowDown 6 times, then Enter
    rel = await tab.find(name="data_subject_relationship", raise_exc=False)
    if not rel:
        return
    await rel.click()
    await asyncio.sleep(0.5)
    for _ in range(6):
        await tab.keyboard.press(Key.ARROWDOWN)
        await asyncio.sleep(0.1)
    await tab.keyboard.press(Key.ENTER)
    await asyncio.sleep(0.5)


async def _submit_request(tab, btn_text, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(8)

    start_btn = await tab.find(text=btn_text, raise_exc=False)
    if not start_btn:
        print(f"{super_scraper.OOPS} '{btn_text}' button not found for {label}")
        return
    await start_btn.scroll_into_view()
    await asyncio.sleep(0.5)
    await start_btn.click_using_js()
    await asyncio.sleep(5)

    fn = await tab.find(name="first_name", raise_exc=False)
    if fn:
        await fn.click()
        await tab.keyboard.type_text(SuperScraper.FIRST_NAME)
    await asyncio.sleep(0.3)

    ln = await tab.find(name="last_name", raise_exc=False)
    if ln:
        await ln.click()
        await tab.keyboard.type_text(SuperScraper.LAST_NAME)
    await asyncio.sleep(0.3)

    em = await tab.find(name="email_address", raise_exc=False)
    if em:
        await em.click()
        await tab.keyboard.type_text(SuperScraper.EMAIL)
    await asyncio.sleep(0.3)

    await _select_relationship(tab)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        await asyncio.sleep(1)
        await tab.take_screenshot(f"inmarket_dry_run_{label}.png")
        print(f"Screenshot saved to inmarket_dry_run_{label}.png")
        return

    review = await tab.find(text="Review Request", raise_exc=False)
    if review:
        await review.click()
        await asyncio.sleep(3)

    submit = await tab.find(text="Submit Request", raise_exc=False)
    if submit:
        await submit.click()
        await asyncio.sleep(5)

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation", "verify")):
        print(f"Submitted '{label}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        print(f"  Note: Check your email ({SuperScraper.EMAIL}) for a verification link to complete the request.")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{label}' — verify in browser")


async def main():
    opts = ChromiumOptions()
    opts.binary_location = "/snap/bin/chromium"
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1280,900")
    super_scraper = SuperScraper()

    requests = list(ALWAYS_REQUESTS)
    if SuperScraper.REMOVE_INFORMATION:
        requests.append(DELETE_REQUEST)

    async with Chrome(options=opts) as browser:
        tab = await browser.start()
        for btn_text, label in requests:
            await _submit_request(tab, btn_text, label, super_scraper)


asyncio.run(main())
