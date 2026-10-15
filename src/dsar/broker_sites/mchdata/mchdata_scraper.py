# mchdata.com — /about/ccpaemail. ASP.NET server-rendered page with
# several unrelated forms sharing generic field ids on the same page
# (login, signup, school-closings newsletter) — the actual CCPA opt-out
# form is the one with `id="email"` (name="Email") and the
# `IsCaliforniaResident` radio group.
# Rights the form exposes: opt-out of sale only — no Access or Delete option on
# this page. Which of them run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP).
# The IsCaliforniaResident radio is answered "Yes" for any privacy-law
# state (a broker honoring CCPA must honor the equivalent request from that
# state's residents) and "No" only for genuine no-law states.
# reCAPTCHA v2 present — **CAPTCHA solution required**; the form is filled and
# left unsubmitted.
#
# Page elements (keep this list current):
#   #email                  Email (name="Email")
#   #MCHCustomerBoolYes     IsCaliforniaResident radio "Yes"
#   #MCHCustomerBoolNo      IsCaliforniaResident radio "No"
#   reCAPTCHA v2 checkbox   manual solve
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.mchdata.com/about/ccpaemail"

EMAIL_FIELD = "email"  # Email
RESIDENT_YES = "MCHCustomerBoolYes"  # IsCaliforniaResident "Yes"
RESIDENT_NO = "MCHCustomerBoolNo"  # IsCaliforniaResident "No"

RIGHT_MAP = {
    Right.RIGHT_TO_OPT_OUT: "opt-out of sale",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        email_field = await tab.find(id=EMAIL_FIELD, raise_exc=False)
        if email_field:
            await email_field.type_text(SuperScraper.EMAIL)
        else:
            print(f"{super_scraper.OOPS} email field not found")

        radio_id = (
            RESIDENT_YES
            if SuperScraper.state_has_privacy_law(SuperScraper.STATE)
            else RESIDENT_NO
        )
        resident_radio = await tab.find(id=radio_id, raise_exc=False)
        if resident_radio:
            await resident_radio.click()
        else:
            print(f"{super_scraper.OOPS} California-resident radio '{radio_id}' not found")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run_opt_out")
        print(
            "\nForm filled but NOT submitted — a reCAPTCHA v2 checkbox is present and "
            "requires a manual solve before submitting."
        )


asyncio.run(main())
