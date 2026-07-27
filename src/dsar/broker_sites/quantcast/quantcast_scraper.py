# quantcast.com — cookie-based DSAR form (data-access.quantserve.com/gdpr/).
# No personal info fields — form identifies users by browser cookies.
# Note: only processes data linked to this specific browser instance.
# Radios: name="request_type" value="retrieval" (Access) or "deletion" (Delete).
# Checkbox: name="data_ownership" (sole-user confirmation).
# reCAPTCHA v2 checkbox — manual solve required in live mode.
# Submit: id="data_request_submit".
# One submission per right (ACCESS always; DELETION gated on REMOVE_INFORMATION).
# Elements found via tab.find() by name/value attributes (querySelectorAll fails
# on this domain for unknown reasons; pydoll CDP-level find works fine).
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://data-access.quantserve.com/gdpr/"


def _is_remove_information():
    v = SuperScraper.REMOVE_INFORMATION
    return isinstance(v, str) and v.strip().upper() in ("TRUE", "1", "YES")


async def _submit_right(tab, super_scraper, radio_value, label):
    """Select radio, check confirmation, take screenshot or await manual submit."""
    radio = await tab.find(
        tag_name="input", **{"name": "request_type", "value": radio_value},
        raise_exc=False
    )
    if not radio:
        print(f"{super_scraper.OOPS} {label} radio not found")
        return

    await radio.click()

    confirm = await tab.find(tag_name="input", **{"name": "data_ownership"}, raise_exc=False)
    if confirm:
        await confirm.click()

    if SuperScraper.DRY_RUN:
        await asyncio.sleep(1)
        await tab.take_screenshot(f"quantcast_dry_run_{radio_value}.png")
        print(
            f"DRY RUN: would submit quantcast '{label}' (cookie-based, no personal info)"
        )
        print(f"Screenshot saved to quantcast_dry_run_{radio_value}.png")
        return

    print(
        f"\n'{label}' form filled. Solve the reCAPTCHA checkbox, "
        "then click Submit Request. Press Enter after the confirmation appears..."
    )
    input()

    src = await tab.page_source
    if any(w in src.lower() for w in ("thank", "success", "received", "submitted", "request")):
        print(f"Submitted '{label}' DSAR (cookie-based)")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{label}' — verify in browser")


async def main():
    options = ChromiumOptions()
    options.binary_location = "/snap/bin/chromium"
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,3000")
    super_scraper = SuperScraper()

    async with Chrome(options=options) as browser:
        tab = await browser.start()

        # ACCESS (always)
        await tab.go_to(URL)
        await asyncio.sleep(5)
        await _submit_right(tab, super_scraper, "retrieval", "Access")

        # DELETION (gated)
        if _is_remove_information():
            await tab.go_to(URL)
            await asyncio.sleep(5)
            await _submit_right(tab, super_scraper, "deletion", "Delete")


asyncio.run(main())
