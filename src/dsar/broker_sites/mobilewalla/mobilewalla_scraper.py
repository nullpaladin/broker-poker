# mobilewalla.com — the recorded URL is just a Privacy Notices page with
# links to per-right policy text and a "Personal Information Requests
# Form" link, which resolves to /global-opt-out-request — the actual form.
# Select-all-that-apply checkboxes — ONE combined submission covers everything checked,
# unlike most other sites in this repo. Rights the form exposes: Deletion, Opt-out of
# sale/share, Access/port a copy, Limit sensitive PI (the last is not automated). Which
# of them run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# The page itself states "regardless of my specific request... all requests will be
# treated as a request for deletion" since Mobilewalla can't otherwise verify identity —
# documented for completeness, doesn't change what gets checked here.
# reCAPTCHA v2 present — **CAPTCHA solution required**; the form is filled and left
# unsubmitted.
#
# Page elements (keep this list current):
#   "Decline"                          cookie banner button
#   input[name=info-request] (no ids, positional in DOM order)
#                                      0=Deletion, 1=Opt-out of sale/share, 2=Access/port a copy,
#                                      3=Limit sensitive PI
#   input[placeholder="Enter Email (Required)"]   Email
#   input[placeholder="Enter MAID (Required)"]    MAID (ADVERTISING_ID)
#   #countryDropdown                   Country <select> -> "United States"
#   #stateDropdown                     State <select> -> STATE
#   input[name=verify-resident] (no ids, positional)   0 = first radio (clicked; old notes call it both "Yes" and "individual consumer" — unverified)
import asyncio

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://www.mobilewalla.com/global-opt-out-request"

# info-request checkbox positions (DOM order)
CHECKBOX_DELETION = 0  # Deletion
CHECKBOX_OPT_OUT = 1  # Opt-out of sale/share
CHECKBOX_ACCESS = 2  # Access/port a copy
CHECKBOX_LIMIT_SENSITIVE = 3  # Limit sensitive PI (not automated)
COUNTRY_SELECT = "countryDropdown"  # Country
STATE_SELECT = "stateDropdown"  # State
EMAIL_PLACEHOLDER = "Enter Email (Required)"  # Email
MAID_PLACEHOLDER = "Enter MAID (Required)"  # MAID

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [CHECKBOX_ACCESS],
    Right.RIGHT_TO_OPT_OUT: [CHECKBOX_OPT_OUT],
    Right.RIGHT_TO_DELETE: [CHECKBOX_DELETION],
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
    checkbox_indexes = [idx for right in rights for idx in RIGHT_MAP[right]]

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        decline_cookies = await tab.find(text="Decline", raise_exc=False)
        if decline_cookies:
            await decline_cookies.click()
            await asyncio.sleep(1)

        checkboxes = await tab.find(xpath="//input[@name='info-request']", find_all=True, raise_exc=False) or []
        for idx in checkbox_indexes:
            if idx < len(checkboxes):
                await checkboxes[idx].click()
            else:
                print(f"{super_scraper.OOPS} checkbox index {idx} not found")

        email_field = await tab.find(xpath=f"//input[@placeholder='{EMAIL_PLACEHOLDER}']", raise_exc=False)
        if email_field:
            await email_field.type_text(SuperScraper.EMAIL)

        maid_field = await tab.find(xpath=f"//input[@placeholder='{MAID_PLACEHOLDER}']", raise_exc=False)
        if maid_field and SuperScraper.ADVERTISING_ID:
            await maid_field.type_text(SuperScraper.ADVERTISING_ID)

        country_select = await tab.find(id=COUNTRY_SELECT, raise_exc=False)
        if country_select:
            await js_utils.select_native_option(country_select, text="United States")
            await asyncio.sleep(1)

        state_select = await tab.find(id=STATE_SELECT, raise_exc=False)
        if state_select:
            await js_utils.select_native_option(state_select, text=SuperScraper.STATE)

        # "Verify you are a resident..." — the first radio is clicked regardless of STATE
        # (unverified against the live page; flagged in the audit report).
        resident_radios = await tab.find(xpath="//input[@name='verify-resident']", find_all=True, raise_exc=False) or []
        if resident_radios:
            await resident_radios[0].click()
        else:
            print(f"{super_scraper.OOPS} verify-resident radios not found")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run_" + "_".join(r.value for r in rights))
        print(
            "\nForm filled but NOT submitted — a reCAPTCHA v2 checkbox is present and "
            "requires a manual solve before submitting."
        )


asyncio.run(main())
