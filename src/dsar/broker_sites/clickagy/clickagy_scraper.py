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
#
# Page elements:
#   "Clickagy has no data associated with your device" banner   Access page, no-data case
#   #ccpa_form_email                                  Email (Access page)
#   #ccpa_form_california_resident_yes / _no          "Are you a California resident?" radios
#   button[type=submit]                               Submit (Opt-Out page)
#   (Access page also has a reCAPTCHA v2 checkbox — manual solve)
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

ACCESS_URL = "https://www.clickagy.com/privacy-center/request/"
OPT_OUT_URL = "https://www.clickagy.com/privacy-center/no-resell/"

# Right -> the page that exercises it.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ACCESS_URL,
    Right.RIGHT_TO_OPT_OUT: OPT_OUT_URL,
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (The two pages have no rights chooser or recorded heading text to inventory.)


async def _select_california_resident(tab, super_scraper):
    # "Are you a California resident?" — answered truthfully from STATE.
    answer_yes = (SuperScraper.STATE or "").strip().lower() == "california"
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
        await SuperScraper.screenshot(tab, "dry_run_access")
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
    await SuperScraper.screenshot(tab, "dry_run_access")
    print(
        "\nAccess request filled but NOT submitted — a reCAPTCHA v2 checkbox requires a manual "
        "solve before submitting."
    )


async def submit_opt_out(tab, super_scraper):
    await tab.go_to(OPT_OUT_URL)
    await asyncio.sleep(4)

    await _select_california_resident(tab, super_scraper)

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, "dry_run_opt_out")
    if SuperScraper.DRY_RUN:
        print("DRY RUN: would submit opt-out-of-sale request for this device/browser")
        return

    submit_button = await tab.find(xpath="//button[@type='submit']", raise_exc=False)
    if submit_button:
        await submit_button.click()
        await asyncio.sleep(3)
        print("Submitted opt-out-of-sale request for this device/browser — confirm in the browser.")
    else:
        print(f"{super_scraper.OOPS} submit button not found")


async def main():
    super_scraper = SuperScraper()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        if Right.RIGHT_TO_ACCESS in rights:
            await submit_access(tab, super_scraper)
        if Right.RIGHT_TO_OPT_OUT in rights:
            await submit_opt_out(tab, super_scraper)


asyncio.run(main())
