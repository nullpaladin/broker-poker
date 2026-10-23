# liveramp.com — LiveRamp's "Your Privacy Choices" portal
# (liveramp.com/privacy/my-privacy-choices/) links out to TrustArc IRM
# request forms. Two of them share the standard react-select Angular scaffold
# (same as ariza.com elsewhere in this repo — "I am" / "Resident of" /
# "Type of Request" comboboxes, container ids
# 00000000-0000-0000-0000-0000000010XX-select-container, text fields
# ...1002fn / ...1002ln / ...1003, hidden consent checkbox ...1007):
#
#   697ea013-8e66-44aa-94c5-fa9d38dd439c  -> "Access Categories of My
#       Information", "Access My Information", "Delete My Information".
#       Picking a request type on this form reveals five more required
#       fields — Street Address / City / State / Zip Code / Phone Number
#       (UUID-named ids, most starting with a digit -> targeted by xpath).
#   ac603fe1-fc25-44b9-8b84-9d87e2d426df  -> "Opt-out (Do Not Sell or Share
#       My Personal Information)"; name + email only, no address fields.
#
# "I am" = "Consumer" on both. This scraper submits one request per type; which
# run is decided only by rights_to_exercise(RIGHT_MAP). Correction lives on a SEPARATE Alpaca-schema form
# (bcdbaba0-9aa6-4fc5-8a1a-2fe02840b72d) with a mandatory "list the incorrect
# information" free-text field — skipped, this repo's persona has no concrete
# inaccuracy to assert.
#
# CAPTCHA differs per form: 697ea013 gates on an invisible reCAPTCHA v2 (site
# key 6LdSn6gUAAAAAKZ5SiEQ8PdCUOgV9sf1ei4utXrB) that may pop a challenge on
# submit; ac603fe1 has a visible distorted-text image CAPTCHA
# (input id "trustarc-captcha-single-line"). Both are filled and left for a
# manual submit.  **CAPTCHA solution required**
#
# NOTE: the name/email/consent ids all start with a digit, so
# tab.find(id=...) builds an invalid CSS selector and silently resolves to
# the wrong (invisible) element — every field is targeted by xpath instead
# (same workaround as ariza.com).
#
# Page elements (TrustArc IRM react-select scaffold):
#   ...1001-select-container   "I am" combobox -> "Consumer"
#   ...1002fn / ...1002ln      First / Last name inputs
#   ...1003                    Email input
#   ...1004-select-container   "Resident of" combobox -> user's state
#   ...1005-select-container   "Type of Request" combobox -> see RIGHT_MAP
#   1d2e11f2-... / 9ad3effb-... / 9e1031aa-... / b1f77941-... / 2ae02c73-...
#                              Street Address / City / State / Zip Code / Phone Number
#                              (only on the access/delete form, revealed after request type)
#   ...1007                    Hidden consent checkbox
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

TRUSTARC = "https://submit-irm.trustarc.com/services/validation/"

IAM_CONTAINER = "00000000-0000-0000-0000-000000001001-select-container"
RESIDENT_CONTAINER = "00000000-0000-0000-0000-000000001004-select-container"
REQUEST_TYPE_CONTAINER = "00000000-0000-0000-0000-000000001005-select-container"

ACCESS_DELETE_FORM = "697ea013-8e66-44aa-94c5-fa9d38dd439c"
OPT_OUT_FORM = "ac603fe1-fc25-44b9-8b84-9d87e2d426df"

# Revealed on ACCESS_DELETE_FORM once a "Type of Request" is chosen. UUID ids,
# most starting with a digit -> must be reached by xpath, not tab.find(id=).
ADDRESS_FIELDS = [
    ("1d2e11f2-720c-4b26-a989-38ecf525f779", "ADDRESS"),
    ("9ad3effb-7e9e-4d06-a534-286258f90fe0", "CITY"),
    ("9e1031aa-72b8-4e12-a6ae-270b62ced633", "STATE"),
    ("b1f77941-7ec1-481c-9524-490e1e3c2431", "ZIP_CODE"),
    ("2ae02c73-329a-4412-804b-f6357eb01fba", "PHONE_NUMBER"),
]

# Right -> list of (form id, "Type of Request" option text), one submission each.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [
        (ACCESS_DELETE_FORM, "Access My Information"),
        (ACCESS_DELETE_FORM, "Access Categories of My Information"),
    ],
    Right.RIGHT_TO_OPT_OUT: [
        (OPT_OUT_FORM, "Opt-out (Do Not Sell or Share My Personal Information)"),
    ],
    Right.RIGHT_TO_DELETE: [(ACCESS_DELETE_FORM, "Delete My Information")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (The options differ per TrustArc form, so one inventory does not fit; per-form capture is needed.)

FIELD_XPATHS = {
    "First name": "//input[@id='00000000-0000-0000-0000-000000001002fn']",
    "Last name": "//input[@id='00000000-0000-0000-0000-000000001002ln']",
    "Email": "//input[@id='00000000-0000-0000-0000-000000001003']",
}


async def _select_option(tab, container_id, text):
    ctrl = await tab.find(
        xpath=f"//div[@id='{container_id}']//div[contains(@class,'select__control')]",
        raise_exc=False,
    )
    if not ctrl:
        return False
    await ctrl.click()
    await asyncio.sleep(0.6)
    await tab.keyboard.type_text(text)
    await asyncio.sleep(1.2)
    opt = await tab.find(
        xpath=f"//div[contains(@class,'select__option') and contains(text(),{text!r})]",
        raise_exc=False,
    )
    if opt:
        await opt.click()
        await asyncio.sleep(0.5)
        return True
    return False


async def submit_request(tab, right, form_id, request_type, super_scraper):
    await tab.go_to(TRUSTARC + form_id)
    await asyncio.sleep(7)

    await _select_option(tab, IAM_CONTAINER, "Consumer")

    first = await tab.find(xpath="//input[@id='00000000-0000-0000-0000-000000001002fn']", raise_exc=False)
    if first:
        await first.scroll_into_view()
        await first.type_text(SuperScraper.FIRST_NAME)
    last = await tab.find(xpath="//input[@id='00000000-0000-0000-0000-000000001002ln']", raise_exc=False)
    if last:
        await last.scroll_into_view()
        await last.type_text(SuperScraper.LAST_NAME)
    email = await tab.find(xpath="//input[@id='00000000-0000-0000-0000-000000001003']", raise_exc=False)
    if email:
        await email.scroll_into_view()
        await email.type_text(SuperScraper.EMAIL)

    await _select_option(tab, RESIDENT_CONTAINER, SuperScraper.STATE)
    await _select_option(tab, REQUEST_TYPE_CONTAINER, request_type)
    await asyncio.sleep(1.5)

    # ACCESS_DELETE_FORM reveals address/phone fields once a request type is
    # picked; OPT_OUT_FORM has none of these (find() just returns None).
    for field_id, attr in ADDRESS_FIELDS:
        value = getattr(SuperScraper, attr, None)
        if not value:
            continue
        field = await tab.find(xpath=f"//input[@id='{field_id}']", raise_exc=False)
        if field:
            await field.scroll_into_view()
            await field.type_text(value)
            await asyncio.sleep(0.2)

    consent = await tab.find(xpath="//input[@id='00000000-0000-0000-0000-000000001007']", raise_exc=False)
    if consent:
        await consent.execute_script(
            "this.checked=true;"
            "this.dispatchEvent(new Event('click', {bubbles:true}));"
            "this.dispatchEvent(new Event('change', {bubbles:true}));"
        )

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    label = request_type.lower().split("(")[0].strip().replace(" ", "_")

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{request_type}' ({right.name}) for {SuperScraper.EMAIL}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
        return

    print(f"\nForm filled for '{request_type}'. Solve the reCAPTCHA if one appears,")
    print("click Submit Request, then press Enter once the confirmation page shows...")
    input()

    print(f"Submitted '{request_type}' ({right.name}) for {SuperScraper.EMAIL} — confirm in the browser.")


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
            for form_id, request_type in RIGHT_MAP[right]:
                await submit_request(tab, right, form_id, request_type, super_scraper)


asyncio.run(main())
