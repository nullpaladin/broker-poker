# hibu.com DSAR scraper — Right to Access, Opt-Out (Sale/Share) and Right to Delete; which
# run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP). "Correct my Personal
# Information" is available on the site but requires specifying what to correct; not
# automated (PAGE_RIGHTS -> None).
# Server-rendered HTML POST form, no captcha. Visitor type always set to
# "Visitor / User of hibu.com or yellowbook.com". Submits once per request type.
#
# Page elements (all ids start with FORM_ID = "form-eng-US-3571-91576_fields_"):
#   VISITOR_TYPE_FIELD  _201064   "Visitor type" -> "Visitor / User of hibu.com or yellowbook.com"
#   REQUEST_TYPE_FIELD  _201067   "Request type"
#   FIRST_NAME_FIELD    _201070   First name
#   LAST_NAME_FIELD     _201073   Last name
#   EMAIL_FIELD         _201076   Email
#   STATE_FIELD         _201079   State
#   ATTEST_CHECKBOX     _201091_0 confirmation checkbox
#   SUBMIT_BUTTON       _201097   Submit button
#   #onetrust-accept-btn-handler  cookie banner "Accept"
import asyncio
import json

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://hibu.com/legal/privacy-form"

VISITOR_TYPE = "Visitor / User of hibu.com or yellowbook.com"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ("Access to my Personal Information", "access"),
    Right.RIGHT_TO_OPT_OUT: ("Opt-out from the Sale or Share of Personal Information", "optout"),
    Right.RIGHT_TO_DELETE: ("Deletion of my Personal Information", "delete"),
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Request-type options the page lists -> Right (None = deliberately not automated).
PAGE_RIGHTS = {
    "Correct my Personal Information": None,
    "Access to my Personal Information": Right.RIGHT_TO_ACCESS,
    "Opt-out from the Sale or Share of Personal Information": Right.RIGHT_TO_OPT_OUT,
    "Deletion of my Personal Information": Right.RIGHT_TO_DELETE,
}

FORM_ID = "form-eng-US-3571-91576_fields_"
VISITOR_TYPE_FIELD = FORM_ID + "201064"  # "Visitor type"
REQUEST_TYPE_FIELD = FORM_ID + "201067"  # "Request type"
FIRST_NAME_FIELD = FORM_ID + "201070"
LAST_NAME_FIELD = FORM_ID + "201073"
EMAIL_FIELD = FORM_ID + "201076"
STATE_FIELD = FORM_ID + "201079"
ATTEST_CHECKBOX = FORM_ID + "201091_0"  # confirmation checkbox
SUBMIT_BUTTON = FORM_ID + "201097"


def _js_set_id(field_id, value):
    fid = json.dumps(field_id)
    val = json.dumps(str(value))
    return (
        f"(function(){{"
        f"var el=document.getElementById({fid});"
        f"if(!el)return;"
        f"el.value={val};"
        f"el.dispatchEvent(new Event('input',{{bubbles:true}}));"
        f"el.dispatchEvent(new Event('change',{{bubbles:true}}));"
        f"}})();"
    )


async def submit_request(tab, request_type, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    await tab.execute_script(
        "var btn=document.getElementById('onetrust-accept-btn-handler');"
        "if(btn)btn.click();"
    )
    await asyncio.sleep(1)

    await tab.execute_script(_js_set_id(VISITOR_TYPE_FIELD, VISITOR_TYPE))
    await tab.execute_script(_js_set_id(REQUEST_TYPE_FIELD, request_type))
    await tab.execute_script(_js_set_id(FIRST_NAME_FIELD, SuperScraper.FIRST_NAME))
    await tab.execute_script(_js_set_id(LAST_NAME_FIELD, SuperScraper.LAST_NAME))
    await tab.execute_script(_js_set_id(EMAIL_FIELD, SuperScraper.EMAIL))
    await tab.execute_script(_js_set_id(STATE_FIELD, SuperScraper.STATE))

    await tab.execute_script(
        f"var cb=document.getElementById('{ATTEST_CHECKBOX}');"
        "if(cb&&!cb.checked)cb.click();"
    )

    await asyncio.sleep(1)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{request_type}' for {SuperScraper.EMAIL}"
        )
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
        return

    await tab.execute_script(
        f"document.getElementById('{SUBMIT_BUTTON}').click();"
    )
    await asyncio.sleep(5)

    print(f"Submitted '{request_type}' for {SuperScraper.EMAIL} — confirm in the browser.")


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
            request_type, label = RIGHT_MAP[right]
            await submit_request(tab, request_type, label, super_scraper)


asyncio.run(main())
