# spglobal.com — S&P Global OneTrust privacy webform
# (privacyportal.onetrust.com). Despite the "Select request type(s)" label the
# request-type role=listbox is SINGLE-select (clicking a second option
# deselects the first) and it only fully renders after State is set — so this
# is one full submission per right.
# Required per pass: "Requesting Party" -> "I am making a request for myself";
# Country (geo, not prefilled) -> United States; State autocomplete combobox;
# a request type; "I am a (an)" role=listbox (Prospective Employee / Customer /
# Contractor / Employee — none fits a data-broker subject, "Customer" used as
# least-wrong); "Does your request involve information found on Panjiva.com?"
# -> "No"; Email / First / Last; Company Name (required — from COMPANY_NAME);
# Address / City / Zip; formField29 "For which division within S&P Global ..."
# combobox -> "Not Sure" (a real run may need one submission per division:
# S&P Global Ratings / S&P Dow Jones Indices / S&P Global Market Intelligence /
# S&P Global Platts / S&P Global Corporate / Panjiva / 451 Research /
# 451 Alliance); requestDetailsDSARElement.
# Exercises Access Data, Do Not Sell my information, Opt-Out of profiling,
# "Obtain list of specific 3rd parties ...", "Correct or update my data"
# unconditionally; "Delete my data" gated on REMOVE_INFORMATION.
# reCAPTCHA v2 requires a manual solve per pass.  **CAPTCHA solution required**
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/5cb57702-8ef7-437e-a62b-408fe78cd310/93391c3d-d6c8-45b1-a169-39a0b7f9fb74"
DIVISION = "Not Sure"

# canonical right code -> (form option label, screenshot/label slug)
RIGHT_MAP = {
    "access": ("Access Data", "access"),
    "opt_out_sale_share": ("Do Not Sell my information", "do_not_sell"),
    "opt_out_profiling": (
        "Opt-Out of profiling in furtherance of decisions that produce legal / similarly significant effects",
        "opt_out_profiling",
    ),
    "know_third_parties": (
        "Obtain list of specific 3rd parties to which personal data was disclosed",
        "third_parties",
    ),
    "correct": ("Correct or update my data", "correct"),
    "delete": ("Delete my data", "delete"),
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def _field_value(field):
    res = await field.execute_script("return this.value;")
    try:
        return (res["result"]["result"]["value"] or "").strip()
    except (KeyError, TypeError):
        return ""


async def _select_combobox(tab, field_id, search_text):
    for _ in range(2):
        field = await tab.find(id=field_id, raise_exc=False)
        if not field:
            return
        if (await _field_value(field)).lower() == search_text.lower():
            return
        await field.click()
        await field.execute_script(
            "this.value=''; this.dispatchEvent(new Event('input',{bubbles:true}));"
        )
        await tab.keyboard.type_text(search_text)
        await asyncio.sleep(2.5)
        clicked = False
        for opt in await tab.find(**{"role": "option"}, find_all=True, raise_exc=False) or []:
            if not await opt.is_visible():
                continue
            label = (opt.get_attribute("aria-label") or opt.text or "").strip()
            if label.lower() == search_text.lower():
                await opt.click_using_js()
                clicked = True
                break
        if not clicked:
            await tab.keyboard.press(Key.ARROWDOWN)
            await asyncio.sleep(0.3)
            await tab.keyboard.press(Key.ENTER)
        await asyncio.sleep(0.6)
        field = await tab.find(id=field_id, raise_exc=False)
        if field and (await _field_value(field)).lower() == search_text.lower():
            return


async def _click_listbox_option(tab, aria_label):
    for opt in await tab.find(**{"aria-label": aria_label, "role": "option"}, find_all=True, raise_exc=False) or []:
        if await opt.is_visible():
            await opt.click_using_js()
            await asyncio.sleep(0.3)
            return True
    return False


async def submit_request(tab, request_type, label, super_scraper, code):
    await tab.go_to(URL)
    await asyncio.sleep(9)

    await _click_listbox_option(tab, "I am making a request for myself")
    await _select_combobox(tab, "countryDSARElement", "United States")
    await asyncio.sleep(1)
    await _select_combobox(tab, "stateDSARElement", SuperScraper.STATE)
    await asyncio.sleep(1.5)  # request-type buttons render after State

    if not await _click_listbox_option(tab, request_type):
        print(f"{super_scraper.OOPS} Request type '{request_type}' not found")
        return
    await _click_listbox_option(tab, "Customer")
    await _click_listbox_option(tab, "No")  # not Panjiva.com data

    # picking a request type can reveal a conditional "What information are you
    # looking to access?" free-text field (required)
    cond = await tab.find(
        xpath="//label[contains(., 'What information are you looking')]/following::input[1]",
        raise_exc=False,
    )
    if cond:
        await cond.type_text(
            "All personal information you hold about me, including its categories, "
            "specific pieces, sources, business purposes, and the third parties it "
            "has been disclosed or sold to."
        )

    await _select_combobox(tab, "formField29DSARElement", DIVISION)

    for fid, value in [
        ("firstNameDSARElement", SuperScraper.FIRST_NAME),
        ("lastNameDSARElement", SuperScraper.LAST_NAME),
        ("emailDSARElement", SuperScraper.EMAIL),
        ("formField37DSARElement", SuperScraper.COMPANY_NAME or "N/A"),
        ("formField49DSARElement", SuperScraper.ADDRESS),
        ("formField50DSARElement", SuperScraper.CITY),
        ("formField51DSARElement", SuperScraper.ZIP_CODE),
    ]:
        el = await tab.find(id=fid, raise_exc=False)
        if el:
            await el.type_text(value)
            await asyncio.sleep(0.2)

    details = await tab.find(id="requestDetailsDSARElement", raise_exc=False)
    if details:
        await details.type_text(SuperScraper.request_statement([code], broker="S&P Global"))

    time.sleep(0.5)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, {
            "First name": "//input[@id='firstNameDSARElement']",
            "Last name": "//input[@id='lastNameDSARElement']",
            "Email": "//input[@id='emailDSARElement']",
            "Request details": "//textarea[@id='requestDetailsDSARElement']",
        })

    submit_btn = await tab.find(id="dsar-webform-submit-button", raise_exc=False)
    if submit_btn:
        await submit_btn.scroll_into_view()
    await SuperScraper.screenshot(tab, f"resources/screenshots/spglobal_dry_run_{label}.png")
    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{request_type}' (division: '{DIVISION}') for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        return

    print(f"\nForm filled for '{request_type}'. Solve the reCAPTCHA, click Submit,")
    print("then press Enter once the confirmation page appears...")
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

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for code in codes:
            request_type, label = RIGHT_MAP[code]
            await submit_request(tab, request_type, label, super_scraper, code)


asyncio.run(main())
