# connectedinvestors.com — First American's shared ServiceNow "Consumer
# Privacy Request Form" (x_farf2_dp_request), branded per-subsidiary via a
# sysparm_id query param. All field ids contain a colon ("IO:7ee7..."),
# which breaks `tab.find(id=...)`'s unescaped CSS selector — every field
# here is targeted by xpath instead, same workaround as the colon-id bug
# documented elsewhere in this repo.
#
# "Please select your state of residence" and "Type of service used"
# (defaults correctly to "Connected Investors") are plain <select>s.
# Selecting a state triggers a server round-trip (ServiceNow catalog client
# script) that populates two otherwise-empty dependent selects — "Request
# Submitted by" (Self (Consumer) used here) and "Select the request type"
# — this takes several seconds; a short wait after selecting the state
# leaves both still empty ("-- None --" only), so a longer wait is used.
# Phone Number intermittently renders with `type="hidden"` depending on the
# exact timing of the form's own async re-renders after the preceding
# selects change — every text field's live `type` attribute and visibility
# are checked immediately before typing, and it's silently skipped if
# either says it isn't a real, visible text field at that moment.
# Request type is a single-select (one submission per right): "Access
# Personal Data" (Access); "Delete Personal Information"
# is Right.RIGHT_TO_DELETE. No Do Not Sell/Opt-Out option exists on this form. "Preferred Response Method" set to Email. The required
# acknowledgement checkbox's actual clickable input has an id prefixed
# "ni." in addition to the colon ("ni.IO:d258b653875b219095280ed7dabb35ab")
# and renders at 1x1px — native `.click()` doesn't reliably toggle it, so
# it's set + dispatched via JS instead. reCAPTCHA v2 requires a manual solve
# in live mode.
import asyncio

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://firstam.service-now.com/x_farf2_dp_request_ci_opt_out.do?sysparm_id=fd58b253875b219095280ed7dabb359a"

STATE_FIELD = "IO:7ee7075387db219095280ed7dabb351c"  # "Please select your state of residence" <select>
SUBMITTED_BY_FIELD = "IO:7e58f653875b219095280ed7dabb355e"  # "Request Submitted by" <select> -> "consumer" (Self (Consumer))
REQUEST_TYPE_FIELD = "IO:c758f653875b219095280ed7dabb35b8"  # "Select the request type" <select> (options in RIGHT_MAP)
RESPONSE_METHOD_FIELD = "IO:f3583a53875b219095280ed7dabb35ab"  # "Preferred Response Method" <select> -> "email"
FIRST_NAME_FIELD = "IO:17583a53875b219095280ed7dabb3513"  # First name
LAST_NAME_FIELD = "IO:d658b653875b219095280ed7dabb35c9"  # Last name
ADDRESS_ONE_FIELD = "IO:c758f653875b219095280ed7dabb357c"  # Address line 1
CITY_FIELD = "IO:0658b653875b219095280ed7dabb3574"  # City
ZIP_FIELD = "IO:1c687a53875b219095280ed7dabb3511"  # ZIP code
PHONE_FIELD = "IO:73583a53875b219095280ed7dabb35b9"  # Phone Number
EMAIL_FIELD = "IO:e258f653875b219095280ed7dabb353a"  # Email
ACKNOWLEDGE_CHECKBOX = "ni.IO:d258b653875b219095280ed7dabb35ab"  # required acknowledgement checkbox (1x1px input)

# Request-type <select> option VALUES (the Delete option's label is "Delete Personal Information").
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Access Personal Data",
    Right.RIGHT_TO_DELETE: "delete",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
RIGHTS_OPTIONS_CSS = f"select[id='{REQUEST_TYPE_FIELD}'] option"  # populated only after the state is chosen


async def _select_by_value(tab, field_id, value, super_scraper, description):
    field = await tab.find(xpath=f"//select[@id='{field_id}']", raise_exc=False)
    if not field:
        print(f"{super_scraper.OOPS} {description} field not found")
        return False
    await js_utils.select_native_option(field, value=value, dispatch=("change",))
    return True


async def submit_request(tab, right, request_type, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    state_abbr = SuperScraper.STATE_ABBREVIATED
    await _select_by_value(tab, STATE_FIELD, state_abbr, super_scraper, "state")
    # dependent selects take several seconds to populate after state changes
    await asyncio.sleep(8)

    await _select_by_value(tab, SUBMITTED_BY_FIELD, "consumer", super_scraper, "'Request Submitted by'")
    await asyncio.sleep(0.5)
    if SuperScraper.HEALTH_CHECK:
        offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
        SuperScraper.audit_rights(offered, PAGE_RIGHTS)

    await _select_by_value(tab, REQUEST_TYPE_FIELD, request_type, super_scraper, "request type")
    await asyncio.sleep(0.5)
    await _select_by_value(tab, RESPONSE_METHOD_FIELD, "email", super_scraper, "'Preferred Response Method'")

    fields = {
        FIRST_NAME_FIELD: SuperScraper.FIRST_NAME,
        LAST_NAME_FIELD: SuperScraper.LAST_NAME,
        ADDRESS_ONE_FIELD: SuperScraper.ADDRESS,
        CITY_FIELD: SuperScraper.CITY,
        ZIP_FIELD: SuperScraper.ZIP_CODE,
        PHONE_FIELD: SuperScraper.PHONE_NUMBER,
        EMAIL_FIELD: SuperScraper.EMAIL,
    }
    for field_id, value in fields.items():
        if not value:
            continue
        field = await tab.find(xpath=f"//input[@id='{field_id}']", raise_exc=False)
        if not field:
            continue
        if await js_utils.js_eval(field, "return this.type;") == "hidden" or not await field.is_visible():
            continue
        await field.type_text(value)

    acknowledge = await tab.find(xpath=f"//input[@id='{ACKNOWLEDGE_CHECKBOX}']", raise_exc=False)
    if acknowledge:
        # custom-styled checkbox rendered at 1x1px — native .click() doesn't
        # reliably toggle it, so check it in JS
        await js_utils.js_check(acknowledge)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, {
            "First name": f"//input[@id='{FIRST_NAME_FIELD}']",
            "Last name": f"//input[@id='{LAST_NAME_FIELD}']",
            "Email": f"//input[@id='{EMAIL_FIELD}']",
            "Address": f"//input[@id='{ADDRESS_ONE_FIELD}']",
            "City": f"//input[@id='{CITY_FIELD}']",
            "Zip": f"//input[@id='{ZIP_FIELD}']",
        })

    if SuperScraper.DRY_RUN:
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
        return

    print(f"\nForm filled for '{right.name}'. Solve the reCAPTCHA, click Submit,")
    print("then press Enter once the confirmation page appears...")
    input()
    print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, right, RIGHT_MAP[right], super_scraper)


asyncio.run(main())
