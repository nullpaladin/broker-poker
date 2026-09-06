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
# "I am" = "Consumer" on both. This scraper submits one request per type:
# both Access variants + Opt-Out unconditionally, Delete gated on
# REMOVE_INFORMATION. Correction lives on a SEPARATE Alpaca-schema form
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
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

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

# (form id, "Type of Request" option text, gated-on-REMOVE_INFORMATION)
REQUESTS = [
    (ACCESS_DELETE_FORM, "Access My Information", False),
    (ACCESS_DELETE_FORM, "Access Categories of My Information", False),
    (OPT_OUT_FORM, "Opt-out (Do Not Sell or Share My Personal Information)", False),
    (ACCESS_DELETE_FORM, "Delete My Information", True),
]


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


async def submit_request(tab, form_id, request_type, super_scraper):
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

    label = request_type.lower().split("(")[0].strip().replace(" ", "_")

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{request_type}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        await asyncio.sleep(1)
        await tab.take_screenshot(path=f"resources/screenshots/liveramp_dry_run_{label}.png")
        print(f"Screenshot saved to resources/screenshots/liveramp_dry_run_{label}.png")
        return

    print(f"\nForm filled for '{request_type}'. Solve the reCAPTCHA if one appears,")
    print("click Submit Request, then press Enter once the confirmation page shows...")
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{request_type}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{request_type}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1400,3000")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for form_id, request_type, gated in REQUESTS:
            if gated and not SuperScraper.REMOVE_INFORMATION:
                continue
            await submit_request(tab, form_id, request_type, super_scraper)


asyncio.run(main())
