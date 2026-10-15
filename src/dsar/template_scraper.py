# <broker>.com — <one-line description of the form: platform, URL, quirks>.
# Rights the form exposes: <list>. Selection is REQUESTED_RIGHTS + per-state gated
# via SuperScraper.rights_to_exercise(RIGHT_MAP); delete is also gated on
# REMOVE_INFORMATION. <note anything the form does NOT support and why.>
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.super_scraper import SuperScraper

URL = ""

# Canonical right code -> this form's entry (label string / value / (value, label) tuple).
RIGHT_MAP = {
    "access": "",
    # "opt_out_sale_share": "",
    # "delete": "",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Set only if the form genuinely cannot run unattended (mid-run SMS/email OTP).
# A manual reCAPTCHA input() pause does NOT count.
# NOT_AUTOMATABLE = True
# NOT_AUTOMATABLE_REASON = ""


async def submit_request(tab, code, super_scraper):
    entry = RIGHT_MAP[code]
    await tab.go_to(URL)
    await asyncio.sleep(5)

    # ... fill fields (SuperScraper.input_text_field / js_set_value / select_native_option) ...
    # ... select the request type from `entry` ...

    message = SuperScraper.request_statement([code], broker="<Broker Name>")
    # ... type `message` into the details/message textarea if the form has one ...

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, {
            # "First name": "//input[@name='first_name']",
        })

    if SuperScraper.DRY_RUN:
        await SuperScraper.screenshot(tab, f"resources/screenshots/<slug>_dry_run_{code}.png")
        print(f"DRY RUN: would submit '{code}' for {SuperScraper.EMAIL}")
        return

    # ... click submit / pause for a manual CAPTCHA solve ...
    source = await SuperScraper.page_text(tab)
    if any(w in source.lower() for w in ("thank you", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{code}' for {SuperScraper.EMAIL}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{code}' — verify in browser")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()
    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for code in codes:
            await submit_request(tab, code, super_scraper)


asyncio.run(main())
