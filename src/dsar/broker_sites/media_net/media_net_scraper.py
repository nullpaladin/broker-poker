# media.net — the "Privacy Rights Requests" section of media.net/preferences/
# is an <iframe id="pr-iframe"> embedding privacyrequest.net (a generic
# third-party DSAR platform; the flavor hash is media.net-specific). The
# iframe is navigable directly and doesn't frame-bust.
#
# Wizard: enter Country ("United States") + State ("Minnesota") in the two
# jQuery-UI autocomplete fields (type, then click the matching <li>), click
# the "Next" <input type=button>. That reveals section 2:
#   "I am a (an)"        -> click the <label class="radio-btn"> "Consumer"
#   "Choose a request type" -> single-select <label class="radio-btn">, one
#                              submission per right
#   First Name / Last Name / Email / Website (honeypot, left blank) /
#   Request Details (required free-text)
# then the Submit button appears.
#
# CAUTION: the rendered form HTML (~150 KB) contains many other
# jurisdictions'/flavors' radio blocks with colliding ids (request-to-access
# etc. reused with different labels) — do NOT target radios by id. The live
# wizard is walked first and every radio is picked by clicking the <label>
# whose visible text matches exactly (unique in this Minnesota flow).
#
# Rights the form exposes (one submission each): "Request to Access Personal Data",
# "Request to Opt-Out (Do Not Sell My Personal Data)", "Request to Delete Personal Data".
# Which of them run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP). The
# other options (targeted-advertising / profiling opt-outs, Rectify, Copy, Appeal) are
# auxiliary and skipped.
#
# An invisible reCAPTCHA (site key 6Lc0__ssAAAAACj7_G92wGzGM-I55b5135O4OsnO)
# may surface a challenge on submit — the form is filled and left for a
# manual submit.  **CAPTCHA solution required**
#
# Page elements (keep this list current):
#   #su-origin_country      Country autocomplete (type, click matching <li>) -> "United States"
#   #su-origin_state        State autocomplete (type, click matching <li>) -> STATE
#   input[type=button] "Next"   reveals section 2
#   label.radio-btn "Consumer"  "I am a (an)"
#   label.radio-btn <request>   "Choose a request type" (matched by exact visible text, never by id)
#   #firstname / #lastname      First Name / Last Name
#   #email-address              Email
#   "website"                   honeypot, left blank
#   #request-details            Request Details (required free text)
#   Submit button / invisible reCAPTCHA   manual
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = (
    "https://privacyrequest.net/privacy-request/"
    "?flavor=098ca9ee3e41231029aac9762ccd6a13"
)

COUNTRY_INPUT = "su-origin_country"  # Country autocomplete
STATE_INPUT = "su-origin_state"  # State autocomplete
FIRST_NAME_INPUT = "firstname"  # First Name
LAST_NAME_INPUT = "lastname"  # Last Name
EMAIL_INPUT = "email-address"  # Email
DETAILS_INPUT = "request-details"  # Request Details

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Request to Access Personal Data",
    Right.RIGHT_TO_OPT_OUT: "Request to Opt-Out (Do Not Sell My Personal Data)",
    Right.RIGHT_TO_DELETE: "Request to Delete Personal Data",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (Only three request types are recorded; the targeted-advertising / profiling / rectify / copy / appeal labels are not.)
RIGHTS_OPTIONS_CSS = "label.radio-btn"  # also matches the "I am a (an)" radios

FIELD_XPATHS = {
    "Country": f"//*[@id='{COUNTRY_INPUT}']",
    "State": f"//*[@id='{STATE_INPUT}']",
    "First name": f"//*[@id='{FIRST_NAME_INPUT}']",
    "Last name": f"//*[@id='{LAST_NAME_INPUT}']",
    "Email": f"//*[@id='{EMAIL_INPUT}']",
    "Request details": f"//*[@id='{DETAILS_INPUT}']",
}


async def _click_li(tab, value):
    li = await tab.find(xpath=f"//li[normalize-space()={value!r}]", raise_exc=False)
    if li:
        await li.click()
        return True
    return False


async def _click_label(tab, text):
    script = (
        "return (function(){var t=%r;"
        "for(var l of document.querySelectorAll('label,span,div')){"
        "if((l.innerText||'').trim()===t){l.scrollIntoView({block:'center'});l.click();return true;}}"
        "return false;})()" % text
    )
    return bool(await js_utils.js_eval(tab, script))


async def _type_input(tab, el_id, value):
    el = await tab.find(id=el_id, raise_exc=False)
    if el:
        await el.click()
        await el.type_text(value)
        await asyncio.sleep(0.3)


async def submit_request(tab, right, request_type, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(9)

    country = await tab.find(id=COUNTRY_INPUT, raise_exc=False)
    await country.click()
    await tab.keyboard.type_text("United States")
    await asyncio.sleep(2.5)
    await _click_li(tab, "United States")
    await asyncio.sleep(1.5)

    state = await tab.find(id=STATE_INPUT, raise_exc=False)
    await state.click()
    await tab.keyboard.type_text(SuperScraper.STATE)
    await asyncio.sleep(2.5)
    await _click_li(tab, SuperScraper.STATE)
    await asyncio.sleep(1.5)

    await js_utils.js_eval(
        tab,
        "return (function(){for(var e of document.querySelectorAll('input[type=button]'))"
        "{if((e.value||'').trim().toLowerCase()==='next'){e.click();return;}}})()",
    )
    await asyncio.sleep(3)

    if not await _click_label(tab, "Consumer"):
        print(f"{super_scraper.OOPS} 'Consumer' option not found for '{request_type}'")
    await asyncio.sleep(1)
    if SuperScraper.HEALTH_CHECK:
        offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
        SuperScraper.audit_rights(offered, PAGE_RIGHTS)

    if not await _click_label(tab, request_type):
        print(f"{super_scraper.OOPS} Request type '{request_type}' not found")
    await asyncio.sleep(2)

    await _type_input(tab, FIRST_NAME_INPUT, SuperScraper.FIRST_NAME)
    await _type_input(tab, LAST_NAME_INPUT, SuperScraper.LAST_NAME)
    await _type_input(tab, EMAIL_INPUT, SuperScraper.EMAIL)
    # "website" is a honeypot — leave blank.
    await _type_input(tab, DETAILS_INPUT, SuperScraper.request_statement([right], broker="Media.net"))

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right.name}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        return

    print(f"\nForm filled for '{request_type}'. Solve the reCAPTCHA if one appears,")
    print("click SUBMIT, then press Enter once the confirmation appears...")
    input()

    print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


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
            await submit_request(tab, right, RIGHT_MAP[right], super_scraper)


asyncio.run(main())
