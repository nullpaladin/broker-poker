# clickagy.com — device/cookie-based tracking, not account-based, so identity
# fields are minimal. Two separate pages:
# - Access (/privacy-center/request/): the page runs its own client-side
#   check of the current browser/device against Clickagy's tracking cookie
#   BEFORE showing anything else, and if it finds no associated data it
#   replaces the entire email+CAPTCHA request form with a "Clickagy has no
#   data associated with your device" banner — the email/CAPTCHA form
#   (id="ccpa_form_email") never renders in that case. A clean automation
#   browser profile with no prior ad-tech tracking history always hits this
#   branch, so the actual report-request form is not exercisable here; the
#   scraper detects the banner and reports that instead of treating it as a
#   failure. If the form ever is visible (e.g. run from a browser profile
#   with real tracking history) it fills email + the California-resident
#   radio and stops for a manual reCAPTCHA v2 solve —
#   **CAPTCHA solution required** in that case.
# - Opt-Out (/privacy-center/no-resell/): only the California-resident radio
#   (asked for statistics only — the site states it honors opt-outs
#   "regardless of location") — no identity fields, no CAPTCHA, so DRY_RUN is
#   respected and a real submission goes through when DRY_RUN is False.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

ACCESS_URL = "https://www.clickagy.com/privacy-center/request/"
OPT_OUT_URL = "https://www.clickagy.com/privacy-center/no-resell/"


async def _select_california_resident(tab, super_scraper):
    # "Are you a California resident?" — answer YES for any state with a privacy
    # law: every such law provides that a business honoring CCPA rights must honor
    # the equivalent request from that state's residents, and many broker forms
    # only ever added CCPA language. NO only for genuine no-privacy-law states.
    answer_yes = SuperScraper.state_has_privacy_law(SuperScraper.STATE)
    radio_id = "ccpa_form_california_resident_yes" if answer_yes else "ccpa_form_california_resident_no"
    radio = await tab.find(id=radio_id, raise_exc=False)
    if radio:
        await radio.click()
    else:
        print(f"{super_scraper.OOPS} California-resident radio '{radio_id}' not found")


async def submit_access(tab, super_scraper):
    await tab.go_to(ACCESS_URL)
    await asyncio.sleep(4)

    no_data_banner = await tab.find(text="Clickagy has no data associated with your device", raise_exc=False)
    if no_data_banner:
        await SuperScraper.screenshot(tab, "resources/screenshots/clickagy_dry_run_access.png")
        print(
            "\nClickagy's own device check reports no data associated with this browser/device — "
            "the email+CAPTCHA request form never rendered, so there is nothing to request."
        )
        return

    email_field = await tab.find(id="ccpa_form_email", raise_exc=False)
    if email_field:
        await email_field.type_text(SuperScraper.EMAIL)
    else:
        print(f"{super_scraper.OOPS} Email field not found")

    await _select_california_resident(tab, super_scraper)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, {"Email": "//input[@id='ccpa_form_email']"})

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, "resources/screenshots/clickagy_dry_run_access.png")
    print(
        "\nAccess request filled but NOT submitted — a reCAPTCHA v2 checkbox requires a manual "
        "solve before submitting."
    )


async def submit_opt_out(tab, super_scraper):
    await tab.go_to(OPT_OUT_URL)
    await asyncio.sleep(4)

    await _select_california_resident(tab, super_scraper)

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, "resources/screenshots/clickagy_dry_run_opt_out.png")
    if SuperScraper.DRY_RUN:
        print("DRY RUN: would submit opt-out-of-sale request for this device/browser")
        return

    submit_button = await tab.find(xpath="//button[@type='submit']", raise_exc=False)
    if submit_button:
        await submit_button.click()
        await asyncio.sleep(3)
        print("Submitted opt-out-of-sale request for this device/browser.")
    else:
        print(f"{super_scraper.OOPS} submit button not found")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await submit_access(tab, super_scraper)
        await submit_opt_out(tab, super_scraper)


asyncio.run(main())
