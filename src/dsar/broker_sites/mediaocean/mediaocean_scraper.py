# mediaocean.com — exercises Access (Obtain Info), Opt-Out (Sale), Delete (gated).
# Marketo form (mktoForm_3843). Fields: FirstName, LastName, Email, State (full name),
# areYoutheConsumer ("Yes"), cCPARequest (request type select). One submission per right.
# No CAPTCHA detected. State uses full name (e.g. "Minnesota").
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://www.mediaocean.com/your-privacy-rights"

# (cCPARequest option value, screenshot label)
REQUESTS = [
    ("CCPA Obtain Info", "access"),
    ("CCPA Opt Out of Sale", "optout"),
]
DELETE_REQUEST = ("CCPA Delete Info", "delete")


async def submit_request(tab, ccpa_value, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    # Dismiss cookie banner if present and visible
    reject = await tab.find(text="Reject all cookies", raise_exc=False)
    if reject and await reject.is_visible():
        await reject.click()
        await asyncio.sleep(1)

    first = await tab.find(id="FirstName", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)

    last = await tab.find(id="LastName", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)

    email = await tab.find(id="Email", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    # State: native <select> with full state name values
    state_select = await tab.find(tag_name="select", id="State", raise_exc=False)
    if state_select:
        state_opt = await state_select.find(
            tag_name="option", value=SuperScraper.STATE.title(), raise_exc=False
        )
        if state_opt:
            await state_opt.click()

    # Are you the consumer: "Yes"
    consumer_select = await tab.find(tag_name="select", id="areYoutheConsumer", raise_exc=False)
    if consumer_select:
        yes_opt = await consumer_select.find(tag_name="option", value="Yes", raise_exc=False)
        if yes_opt:
            await yes_opt.click()

    # Request type
    ccpa_select = await tab.find(tag_name="select", id="cCPARequest", raise_exc=False)
    if ccpa_select:
        ccpa_opt = await ccpa_select.find(tag_name="option", value=ccpa_value, raise_exc=False)
        if ccpa_opt:
            await ccpa_opt.click()
    else:
        print(f"{super_scraper.OOPS} cCPARequest select not found")
        return

    time.sleep(0.5)

    if SuperScraper.DRY_RUN:
        submit_btn = await tab.find(tag_name="button", text="Submit", raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await tab.take_screenshot(f"resources/screenshots/mediaocean_dry_run_{label}.png")
        print(
            f"DRY RUN: would submit '{label}' ({ccpa_value}) for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        return

    submit_btn = await tab.find(tag_name="button", text="Submit", raise_exc=False)
    if submit_btn:
        await submit_btn.click()
    await asyncio.sleep(5)

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "submitted", "received", "confirmation")):
        print(f"Submitted '{label}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{label}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    requests = list(REQUESTS)
    if SuperScraper.REMOVE_INFORMATION:
        requests.append(DELETE_REQUEST)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for ccpa_value, label in requests:
            await submit_request(tab, ccpa_value, label, super_scraper)


asyncio.run(main())
