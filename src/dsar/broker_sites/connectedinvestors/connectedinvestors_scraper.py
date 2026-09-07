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
# Personal Data" (Access) unconditionally; "Delete Personal Information"
# gated on REMOVE_INFORMATION. No Do Not Sell/Opt-Out option exists on this
# form. "Preferred Response Method" set to Email. The required
# acknowledgement checkbox's actual clickable input has an id prefixed
# "ni." in addition to the colon ("ni.IO:d258b653875b219095280ed7dabb35ab")
# and renders at 1x1px — native `.click()` doesn't reliably toggle it, so
# it's set + dispatched via JS instead. reCAPTCHA v2 requires a manual solve
# in live mode.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://firstam.service-now.com/x_farf2_dp_request_ci_opt_out.do?sysparm_id=fd58b253875b219095280ed7dabb359a"

STATE_FIELD = "IO:7ee7075387db219095280ed7dabb351c"
SUBMITTED_BY_FIELD = "IO:7e58f653875b219095280ed7dabb355e"
REQUEST_TYPE_FIELD = "IO:c758f653875b219095280ed7dabb35b8"
RESPONSE_METHOD_FIELD = "IO:f3583a53875b219095280ed7dabb35ab"
FIRST_NAME_FIELD = "IO:17583a53875b219095280ed7dabb3513"
LAST_NAME_FIELD = "IO:d658b653875b219095280ed7dabb35c9"
ADDRESS_ONE_FIELD = "IO:c758f653875b219095280ed7dabb357c"
CITY_FIELD = "IO:0658b653875b219095280ed7dabb3574"
ZIP_FIELD = "IO:1c687a53875b219095280ed7dabb3511"
PHONE_FIELD = "IO:73583a53875b219095280ed7dabb35b9"
EMAIL_FIELD = "IO:e258f653875b219095280ed7dabb353a"
ACKNOWLEDGE_CHECKBOX = "ni.IO:d258b653875b219095280ed7dabb35ab"

REQUEST_TYPES = ["Access Personal Data"]
DELETE_REQUEST_TYPE = "delete"


async def _select_by_value(tab, field_id, value, super_scraper, description):
    field = await tab.find(xpath=f"//select[@id='{field_id}']", raise_exc=False)
    if not field:
        print(f"{super_scraper.OOPS} {description} field not found")
        return False
    await field.execute_script(
        "for (var i=0;i<this.options.length;i++){"
        f"  if(this.options[i].value==={value!r}){{ this.selectedIndex=i; }}"
        "}"
        "this.dispatchEvent(new Event('change', {bubbles:true}));"
    )
    return True


async def submit_request(tab, request_type, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    state_abbr = SuperScraper.STATE_ABBREVIATED
    await _select_by_value(tab, STATE_FIELD, state_abbr, super_scraper, "state")
    # dependent selects take several seconds to populate after state changes
    await asyncio.sleep(8)

    await _select_by_value(tab, SUBMITTED_BY_FIELD, "consumer", super_scraper, "'Request Submitted by'")
    await asyncio.sleep(0.5)
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
        current_type = await field.execute_script("return this.type;")
        if current_type["result"]["result"]["value"] == "hidden" or not await field.is_visible():
            continue
        await field.type_text(value)

    acknowledge = await tab.find(xpath=f"//input[@id='{ACKNOWLEDGE_CHECKBOX}']", raise_exc=False)
    if acknowledge:
        # custom-styled checkbox rendered at 1x1px — native .click() doesn't
        # reliably toggle it, set + dispatch events instead
        await acknowledge.execute_script(
            "this.checked=true;"
            "this.dispatchEvent(new Event('click', {bubbles:true}));"
            "this.dispatchEvent(new Event('change', {bubbles:true}));"
        )

    label = request_type.lower().replace(" ", "_")

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{request_type}' request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/connectedinvestors_dry_run_{label}.png")
        return

    print(f"\nForm filled for '{request_type}'. Solve the reCAPTCHA, click Submit,")
    print("then press Enter once the confirmation page appears...")
    input()
    print(f"Submitted '{request_type}' request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    request_types = list(REQUEST_TYPES)
    if SuperScraper.REMOVE_INFORMATION:
        request_types.append(DELETE_REQUEST_TYPE)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for request_type in request_types:
            await submit_request(tab, request_type, super_scraper)


asyncio.run(main())
