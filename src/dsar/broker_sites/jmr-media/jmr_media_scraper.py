# jmr-media.com — exercises Opt-Out of Sale/Share, Limit Sensitive PI, Access,
# and Right to Delete (gated on REMOVE_INFORMATION). Correct skipped (requires
# specifying what to correct). React/Next.js form with Cloudflare Turnstile
# that auto-completes in a real Chromium browser (no manual solve needed).
# State is a native <select id="state"> with 2-letter abbreviation values.
# id="website" is a honeypot — not touched. Submits one request per right type.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://jmr-media.com/do-not-sell"

# (requestType value, screenshot label)
REQUESTS = [
    ("opt_out_sale_share", "optout"),
    ("limit_sensitive_pi", "sensitive"),
    ("access_request", "access"),
]
DELETE_REQUEST = ("delete_request", "delete")


async def submit_request(tab, request_value, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)  # allow Turnstile to auto-complete

    first = await tab.find(id="firstName", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)

    last = await tab.find(id="lastName", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)

    email = await tab.find(id="email", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    state_abbr = await SuperScraper.state_full_name_to_abbreviated(SuperScraper.STATE)
    state_select = await tab.find(id="state", raise_exc=False)
    if state_select:
        state_opt = await state_select.find(tag_name="option", value=state_abbr, raise_exc=False)
        if state_opt:
            await state_opt.click()

    radio = await tab.find(
        xpath=f"//input[@name='requestType'][@value='{request_value}']",
        raise_exc=False,
    )
    if not radio:
        print(f"{super_scraper.OOPS} Radio '{request_value}' not found")
        return
    await radio.click()

    time.sleep(0.5)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{request_value}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        await tab.take_screenshot(f"jmr_media_dry_run_{label}.png")
        print(f"Screenshot saved to jmr_media_dry_run_{label}.png")
        return

    submit = await tab.find(text="Submit Request", raise_exc=False)
    if not submit:
        submit = await tab.find(tag_name="button", raise_exc=False)
    if submit:
        await submit.click()
    await asyncio.sleep(4)

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{request_value}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{request_value}' — verify in browser")


async def main():
    options = ChromiumOptions()
    options.binary_location = "/snap/bin/chromium"
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,2400")
    super_scraper = SuperScraper()

    requests = list(REQUESTS)
    if SuperScraper.REMOVE_INFORMATION:
        requests.append(DELETE_REQUEST)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for request_value, label in requests:
            await submit_request(tab, request_value, label, super_scraper)


asyncio.run(main())
