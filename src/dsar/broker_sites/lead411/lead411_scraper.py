# lead411.com — your-privacy-choices/. "Request Type" select
# (`user_option_request_for_profile`) offers Access/Opt-out of Sale/Know
# What Is Processed/Correct/Delete/Port — one submission per type; Know/
# Correct/Port are not automated. Which rights run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). Selecting Country=United States reveals a State select
# (`us-states`, initially `display:none`). Email + a required "I Agree"
# checkbox + reCAPTCHA v2 checkbox gate the "Get Code" button, which emails
# a real verification code — a side-effect trigger, so this scraper fills
# the form and stops there regardless of DRY_RUN. A Cookiebot cookie-
# consent banner also offers its own one-click "Do not sell or share my
# personal information" button directly in the banner — dismissed via the
# main "OK" accept instead so it doesn't interfere with clicking through
# the actual form fields (that shortcut button is a separate, redundant
# opt-out mechanism outside the request form itself). **CAPTCHA solution
# required** for reCAPTCHA regardless.
#
# Page elements:
#   #CybotCookiebotDialogBodyButtonAccept   Cookie banner "OK" accept
#   #select_option_for_profile              "Request Type" <select> (options: see RIGHT_MAP)
#   #countries                              Country <select> -> "United States"
#   #us-states                              State <select> (revealed after Country)
#   #employee_email                         Email
#   #i_agree                                "I Agree" checkbox (custom-styled)
#   reCAPTCHA v2 checkbox + "Get Code" button (emails a verification code)
import asyncio

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://www.lead411.com/your-privacy-choices/"

NOT_AUTOMATABLE = True
NOT_AUTOMATABLE_REASON = (
    "submission requires an emailed verification code (OTP)"
)

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Access My Personal Information"],
    Right.RIGHT_TO_OPT_OUT: ["Opt-out of the Sale of My Personal Information"],
    Right.RIGHT_TO_DELETE: ["Delete My Personal Information"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (NOT_AUTOMATABLE: no running path is added. Only three of the six "Request Type" labels are recorded verbatim.)


async def submit_request(tab, right, request_type, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    accept_btn = await tab.find(id="CybotCookiebotDialogBodyButtonAccept", raise_exc=False)
    if accept_btn:
        await accept_btn.click()
        await asyncio.sleep(1)

    request_select = await tab.find(id="select_option_for_profile", raise_exc=False)
    if request_select:
        await js_utils.select_native_option(request_select, text=request_type, dispatch=("change",))

    country_select = await tab.find(id="countries", raise_exc=False)
    if country_select:
        await js_utils.select_native_option(country_select, text='United States', dispatch=("change",))
        await asyncio.sleep(1)

    state_select = await tab.find(id="us-states", raise_exc=False)
    if state_select:
        await js_utils.select_native_option(state_select, text=SuperScraper.STATE, dispatch=("change",))

    email_field = await tab.find(id="employee_email", raise_exc=False)
    if email_field:
        await email_field.type_text(SuperScraper.EMAIL)

    agree_checkbox = await tab.find(id="i_agree", raise_exc=False)
    if agree_checkbox:
        # native .click() raises ElementNotVisible — the real <input> is
        # visually replaced by custom checkbox styling; set + dispatch via
        # JS instead
        await agree_checkbox.execute_script(
            "this.checked=true;"
            "this.dispatchEvent(new Event('click', {bubbles:true}));"
            "this.dispatchEvent(new Event('change', {bubbles:true}));"
        )

    label = request_type.lower().replace(" ", "_").replace("-", "_")

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{label}")
    print(
        f"\n'{right.name}' ({request_type}) request filled but NOT sent — solve the reCAPTCHA and click "
        "'Get Code' yourself, then enter the verification code you receive. This emails a "
        "real code regardless of DRY_RUN, so it is never done automatically."
    )


async def main():
    if SuperScraper.bail_if_not_automatable(globals()):
        return
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            for request_type in RIGHT_MAP[right]:
                await submit_request(tab, right, request_type, super_scraper)


asyncio.run(main())
