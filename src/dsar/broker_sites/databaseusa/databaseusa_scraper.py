# databaseusa.com — Contact Form 7 "MCDPA Request Page" (Minnesota Consumer
# Data Privacy Act). A single generic request form (no discrete Access/
# Delete/Opt-Out picker) covering all 7 MCDPA rights at once (know/access,
# delete, correct, data portability, opt out of targeted advertising, opt
# out of sale, opt out of profiling) via one Email/Full Name/State
# submission. The CF7 form key is literally "email-authentication" — this is
# an email-verification gate (fill in and a verification link is emailed),
# so this scraper fills the fields and stops there regardless of DRY_RUN;
# clicking Send actually triggers that email and must be done manually.
#
# Residency: the page is the Minnesota MCDPA request page, so it is only for residents of a
# state with a privacy law.
#
# Page elements:
#   input[name=email]       Email
#   input[name=fullname]    Full Name
#   #state                  State <select> (option values are state abbreviations)
#   "Send" button           Sends the verification email — never clicked here
import asyncio

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://privacycompliance.biz/databaseusa-mcdpa/"

SERVES_NO_LAW_STATES = False

# One generic request covers every right the form lists; it cannot be narrowed per right.
GENERAL_MCDPA_REQUEST = "MCDPA request"
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: GENERAL_MCDPA_REQUEST,
    Right.RIGHT_TO_OPT_OUT: GENERAL_MCDPA_REQUEST,
    Right.RIGHT_TO_DELETE: GENERAL_MCDPA_REQUEST,
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_state_unsupported(globals()):
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

        email_field = await tab.find(xpath="//input[@name='email']", raise_exc=False)
        name_field = await tab.find(xpath="//input[@name='fullname']", raise_exc=False)
        state_select = await tab.find(id="state", raise_exc=False)

        if email_field:
            await email_field.type_text(SuperScraper.EMAIL)
        if name_field:
            await name_field.type_text(f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        if state_select:
            state_abbr = SuperScraper.STATE_ABBREVIATED
            await js_utils.select_native_option(state_select, value=state_abbr, dispatch=("change",))

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run_general_request")
        print(
            "\nMCDPA request form filled but NOT sent — click 'Send' yourself, check your "
            "inbox for the verification link, and click it to complete the request. This "
            "sends a real verification email regardless of DRY_RUN, so it is never done "
            "automatically."
        )


asyncio.run(main())
