# fmadata.com — /opt-out-requests/new Rails-rendered form, POSTs in place.
# One submission per right via the opt_out_request[request_type] <select>:
#   - "Opt out"    (opt_out)    -> Opt-Out
#   - "Disclosure" (disclosure) -> Access
#   - "Deletion"   (deletion)   -> Delete
# Fields: opt_out_request[name] (full name), [street_address], [city], [state],
# [postal_code]; is_authorized_agent radio -> "false"; [authorized_agent_name]
# left blank. Note: this form has NO email field. Ends in an hCaptcha widget —
# filled to that point and left for a manual solve + Submit.
# **CAPTCHA solution required**
#
# Page elements:
#   #opt_out_request_request_type              "request_type" select
#   #opt_out_request_name                      Full name
#   #opt_out_request_street_address / _city / _state / _postal_code   Street address / City / State / Postal code
#   #opt_out_request_is_authorized_agent_false is_authorized_agent radio -> "No"
#   hCaptcha widget + Submit                   left for the user
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper
from src.dsar import js_utils

URL = "https://www.fmadata.com/opt-out-requests/new"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("disclosure", "access")],
    Right.RIGHT_TO_OPT_OUT: [("opt_out", "opt_out")],
    Right.RIGHT_TO_DELETE: [("deletion", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every option in the request_type <select>, as displayed -> the Right it maps to.
PAGE_RIGHTS = {
    "Opt out": Right.RIGHT_TO_OPT_OUT,
    "Disclosure": Right.RIGHT_TO_ACCESS,
    "Deletion": Right.RIGHT_TO_DELETE,
}
RIGHTS_OPTIONS_CSS = "#opt_out_request_request_type option"

FIELD_XPATHS = {
    "Full name": "//*[@id='opt_out_request_name']",
    "Street address": "//*[@id='opt_out_request_street_address']",
    "City": "//*[@id='opt_out_request_city']",
    "State": "//*[@id='opt_out_request_state']",
    "Postal code": "//*[@id='opt_out_request_postal_code']",
}


async def submit_request(tab, right, request_type, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(4)

    if SuperScraper.HEALTH_CHECK:
        offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
        SuperScraper.audit_rights(offered, PAGE_RIGHTS)

    rt = await tab.find(id="opt_out_request_request_type", raise_exc=False)
    if not rt:
        print(f"{super_scraper.OOPS} request_type select not found")
        return
    await js_utils.select_native_option(rt, value=request_type)
    await asyncio.sleep(0.3)

    full_name = " ".join(p for p in (SuperScraper.FIRST_NAME, SuperScraper.LAST_NAME) if p)
    state_value = SuperScraper.STATE
    fields = {
        "opt_out_request_name": full_name,
        "opt_out_request_street_address": SuperScraper.ADDRESS,
        "opt_out_request_city": SuperScraper.CITY,
        "opt_out_request_state": state_value,
        "opt_out_request_postal_code": SuperScraper.ZIP_CODE,
    }
    for field_id, val in fields.items():
        if not val:
            continue
        el = await tab.find(id=field_id, raise_exc=False)
        if el:
            await el.type_text(val)
            await asyncio.sleep(0.15)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    agent_no = await tab.find(id="opt_out_request_is_authorized_agent_false", raise_exc=False)
    if agent_no:
        await agent_no.click()
    else:
        print(f"{super_scraper.OOPS} authorized-agent 'No' radio not found")

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
    print(
        f"'{right.name}' request filled but NOT submitted — solve the hCaptcha "
        f"manually, then click Submit."
    )


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
        for right in rights:
            for request_type, _label in RIGHT_MAP[right]:
                await submit_request(tab, right, request_type, super_scraper)


asyncio.run(main())
