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
# Rights exercised (one submission each): "Request to Access Personal Data"
# and "Request to Opt-Out (Do Not Sell My Personal Data)" unconditionally;
# "Request to Delete Personal Data" gated on REMOVE_INFORMATION. The other
# options (targeted-advertising / profiling opt-outs, Rectify, Copy, Appeal)
# are auxiliary and skipped.
#
# An invisible reCAPTCHA (site key 6Lc0__ssAAAAACj7_G92wGzGM-I55b5135O4OsnO)
# may surface a challenge on submit — the form is filled and left for a
# manual submit.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = (
    "https://privacyrequest.net/privacy-request/"
    "?flavor=098ca9ee3e41231029aac9762ccd6a13"
)

REQUESTS = [
    ("Request to Access Personal Data", "access", False),
    ("Request to Opt-Out (Do Not Sell My Personal Data)", "opt_out", False),
    ("Request to Delete Personal Data", "delete", True),
]

DETAILS = (
    "I am a {state} resident and I am exercising my privacy rights under the {law} "
    "with respect to the personal information Media.net and its partners hold "
    "about me: {req}."
)


def _details_for(request_type):
    return DETAILS.format(
        state=SuperScraper.STATE,
        law=SuperScraper.LAW_FULL_NAME or "applicable state and federal privacy law",
        req=request_type,
    )


async def _click_li(tab, value):
    li = await tab.find(xpath=f"//li[normalize-space()={value!r}]", raise_exc=False)
    if li:
        await li.click()
        return True
    return False


async def _click_label(tab, text):
    code = (
        "return (function(){var t=%r;"
        "for(var l of document.querySelectorAll('label,span,div')){"
        "if((l.innerText||'').trim()===t){l.scrollIntoView({block:'center'});l.click();return true;}}"
        "return false;})()" % text
    )
    r = await tab.execute_script(code)
    return bool(r["result"]["result"].get("value"))


async def _type_input(tab, el_id, value):
    el = await tab.find(id=el_id, raise_exc=False)
    if el:
        await el.click()
        await el.type_text(value)
        await asyncio.sleep(0.3)


async def submit_request(tab, request_type, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(9)

    country = await tab.find(id="su-origin_country", raise_exc=False)
    await country.click()
    await tab.keyboard.type_text("United States")
    await asyncio.sleep(2.5)
    await _click_li(tab, "United States")
    await asyncio.sleep(1.5)

    state = await tab.find(id="su-origin_state", raise_exc=False)
    await state.click()
    await tab.keyboard.type_text(SuperScraper.STATE)
    await asyncio.sleep(2.5)
    await _click_li(tab, SuperScraper.STATE)
    await asyncio.sleep(1.5)

    await tab.execute_script(
        "return (function(){for(var e of document.querySelectorAll('input[type=button]'))"
        "{if((e.value||'').trim().toLowerCase()==='next'){e.click();return;}}})()"
    )
    await asyncio.sleep(3)

    if not await _click_label(tab, "Consumer"):
        print(f"{super_scraper.OOPS} 'Consumer' option not found for '{request_type}'")
    await asyncio.sleep(1)
    if not await _click_label(tab, request_type):
        print(f"{super_scraper.OOPS} Request type '{request_type}' not found")
    await asyncio.sleep(2)

    await _type_input(tab, "firstname", SuperScraper.FIRST_NAME)
    await _type_input(tab, "lastname", SuperScraper.LAST_NAME)
    await _type_input(tab, "email-address", SuperScraper.EMAIL)
    # "website" is a honeypot — leave blank.
    await _type_input(tab, "request-details", _details_for(request_type))

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/media_net_dry_run_{label}.png")
    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{request_type}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        return

    print(f"\nForm filled for '{request_type}'. Solve the reCAPTCHA if one appears,")
    print("click SUBMIT, then press Enter once the confirmation appears...")
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

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for request_type, label, gated in REQUESTS:
            if gated and not SuperScraper.wants("delete"):
                continue
            await submit_request(tab, request_type, label, super_scraper)


asyncio.run(main())
