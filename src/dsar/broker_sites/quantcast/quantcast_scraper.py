# quantcast.com — cookie-based DSAR form (data-access.quantserve.com/gdpr/).
# No personal info fields — form identifies users by browser cookies.
# Note: only processes data linked to this specific browser instance.
# Radios: name="request_type" value="retrieval" (Access) or "deletion" (Delete).
# Checkbox: name="data_ownership" (sole-user confirmation).
# reCAPTCHA v2 checkbox — manual solve required in live mode.
# Submit: id="data_request_submit".
# One submission per right. The form only exposes GDPR retrieval/deletion (no
# opt-out), so which rights run is REQUESTED_RIGHTS + per-state gated, with
# deletion also gated on REMOVE_INFORMATION (via SuperScraper.rights_to_exercise).
# Elements found via tab.find() by name/value attributes (querySelectorAll fails
# on this domain for unknown reasons; pydoll CDP-level find works fine).
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://data-access.quantserve.com/gdpr/"

# Canonical right code -> this form's request_type radio value.
RIGHT_MAP = {"access": "retrieval", "delete": "deletion"}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


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

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(
            tab,
            {
                f"{label} request_type radio": f"//input[@name='request_type' and @value='{radio_value}']",
                "sole-user confirmation": "//input[@name='data_ownership']",
            },
        )

    if SuperScraper.DRY_RUN:
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/quantcast_dry_run_{radio_value}.png")
        print(
            f"DRY RUN: would submit quantcast '{label}' (cookie-based, no personal info)"
        )
        return

    print(
        f"\n'{label}' form filled. Solve the reCAPTCHA checkbox, "
        "then click Submit Request. Press Enter after the confirmation appears..."
    )
    input()

    src = await tab.page_source
    if any(w in src.lower() for w in ("thank you", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{label}' DSAR (cookie-based)")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{label}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for code in codes:
            await tab.go_to(URL)
            await asyncio.sleep(5)
            await _submit_right(tab, super_scraper, RIGHT_MAP[code], code.capitalize())


asyncio.run(main())
