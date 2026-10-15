# quantcast.com — cookie-based DSAR form (data-access.quantserve.com/gdpr/).
# No personal info fields — form identifies users by browser cookies.
# Note: only processes data linked to this specific browser instance.
# Radios: name="request_type" value="retrieval" (Access) or "deletion" (Delete).
# Checkbox: name="data_ownership" (sole-user confirmation).
# reCAPTCHA v2 checkbox — manual solve required in live mode.
# Submit: id="data_request_submit".
# One submission per right. The form only exposes retrieval/deletion (no opt-out);
# which of them run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# Elements found via tab.find() by name/value attributes (querySelectorAll fails
# on this domain for unknown reasons; pydoll CDP-level find works fine).
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://data-access.quantserve.com/gdpr/"

# Right -> this form's request_type radio value.
RIGHT_MAP = {Right.RIGHT_TO_ACCESS: "retrieval", Right.RIGHT_TO_DELETE: "deletion"}
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
        await SuperScraper.screenshot(tab, f"dry_run_{radio_value}")
        print(
            f"DRY RUN: would submit quantcast '{label}' (cookie-based, no personal info)"
        )
        return

    print(
        f"\n'{label}' form filled. Solve the reCAPTCHA checkbox, "
        "then click Submit Request. Press Enter after the confirmation appears..."
    )
    input()

    print(f"Submitted '{label}' DSAR (cookie-based) — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await tab.go_to(URL)
            await asyncio.sleep(5)
            await _submit_right(tab, super_scraper, RIGHT_MAP[right], right.name)


asyncio.run(main())
