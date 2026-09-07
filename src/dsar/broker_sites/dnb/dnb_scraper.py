# dnb.com (Dun & Bradstreet) — TrustArc IRM privacy request form
# (submit-irm.trustarc.eu). Same react-select scaffold as ariza.com elsewhere
# in this repo: container ids 00000000-...-0000000010{01,04,05} for "I Am",
# "Resident of" (state/country full names) and "Type of Request" (single-select
# — the options only populate after "Resident of" is chosen), driven by
# clicking the .select__control, typing, then clicking the matching
# .select__option. Name fields are ...1002fn / ...1002ln, email is ...1003
# (ids start with a digit, so targeted by xpath — `tab.find(id=...)` builds an
# invalid CSS selector for these).
# D&B additionally has a "which data" checkbox group — "Consumer Data" and
# "Professional Contact Data" are checked (a data-broker subject's personal
# data); "Business Data" and the per-"Company 1" fields (D-U-N-S number, etc.)
# are left blank. One submission per right — Access, Opt-Out, Do Not Sell/Share,
# Correct unconditionally; Delete gated on REMOVE_INFORMATION.
# reCAPTCHA v2 requires a manual solve. This TrustArc host can also throw a
# PerimeterX "confirm you are human" wall after rapid repeated requests — retry
# from a fresh session if so.  **CAPTCHA solution required**
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://submit-irm.trustarc.eu/services/validation/ba81b98f-997d-4216-b4cc-d64cf261b082"

IAM_CONTAINER = "00000000-0000-0000-0000-000000001001-select-container"
RESIDENT_CONTAINER = "00000000-0000-0000-0000-000000001004-select-container"
REQUEST_TYPE_CONTAINER = "00000000-0000-0000-0000-000000001005-select-container"

RIGHT_MAP = {
    "access": ["Access My Information"],
    "correct": ["Correct or Update My Information"],
    "opt_out_sale_share": [
        "Do not Sell or Share My Personal Information",
        "Opt-out or Unsubscribe",
    ],
    "delete": ["Delete My Information"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)
DATA_CATEGORIES = ["Consumer Data", "Professional Contact Data"]


async def _select_option(tab, container_id, text):
    ctrl = await tab.find(
        xpath=f"//div[@id='{container_id}']//div[contains(@class,'select__control')]",
        raise_exc=False,
    )
    if not ctrl:
        return False
    await ctrl.click()
    await asyncio.sleep(0.5)
    await tab.keyboard.type_text(text)
    await asyncio.sleep(1)
    opt = await tab.find(
        xpath=f"//div[contains(@class,'select__option') and contains(text(),{text!r})]",
        raise_exc=False,
    )
    if opt:
        await opt.click()
        await asyncio.sleep(0.5)
        return True
    return False


async def submit_request(tab, right, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    await _select_option(tab, IAM_CONTAINER, "Individual")

    for cat in DATA_CATEGORIES:
        box = await tab.find(**{"aria-label": cat}, raise_exc=False)
        if box:
            await box.execute_script("if (!this.checked) this.click();")
            await asyncio.sleep(0.1)

    for xpath, value in [
        ("//input[@id='00000000-0000-0000-0000-000000001002fn']", SuperScraper.FIRST_NAME),
        ("//input[@id='00000000-0000-0000-0000-000000001002ln']", SuperScraper.LAST_NAME),
        ("//input[@id='00000000-0000-0000-0000-000000001003']", SuperScraper.EMAIL),
    ]:
        el = await tab.find(xpath=xpath, raise_exc=False)
        if el:
            await el.scroll_into_view()
            await el.type_text(value)

    await _select_option(tab, RESIDENT_CONTAINER, SuperScraper.STATE)
    await _select_option(tab, REQUEST_TYPE_CONTAINER, right)

    # accuracy attestation checkbox (custom-styled hidden input on TrustArc)
    for consent in await tab.find(xpath="//input[@type='checkbox']", find_all=True, raise_exc=False) or []:
        aria = (consent.get_attribute("aria-label") or "").lower()
        if aria in ("", "i attest", "consent") or "accurate" in aria or "attest" in aria:
            if aria in [c.lower() for c in DATA_CATEGORIES]:
                continue
            await consent.execute_script(
                "this.checked=true;"
                "this.dispatchEvent(new Event('click',{bubbles:true}));"
                "this.dispatchEvent(new Event('change',{bubbles:true}));"
            )

    label = right.lower().replace(" ", "_").replace("/", "_")
    time.sleep(0.5)
    await SuperScraper.screenshot(tab, f"resources/screenshots/dnb_dry_run_{label}.png")
    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        return

    print(f"\nForm filled for '{right}'. Solve the reCAPTCHA, click Submit,")
    print("then press Enter once the confirmation page appears...")
    input()


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    rights = [entry for code in codes for entry in RIGHT_MAP[code]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, right, super_scraper)


asyncio.run(main())
