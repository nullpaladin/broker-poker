# kalibrate.com (intalytics.com) — OneTrust UK privacy webform
# (privacyportal-uk.onetrust.com), embedded on kalibrate.com/dsr-form/ via a
# src'd iframe; go direct.
# Angular form. "Select request type(s)" (requestTypesDSARElement listbox):
# "Right to Know/Access to Information", "Data Deletion/Opt-out/Do Not Sell"
# (a COMBINED option), "Object to Processing", "Rectify Personal Data",
# "Unsubscribe from Marketing" — one submission per right: Access + Object to
# Processing unconditional; "Data Deletion/Opt-out/Do Not Sell" gated on
# REMOVE_INFORMATION (it bundles deletion); Rectify + Unsubscribe skipped.
# "Have you read and consented to the Privacy Policy?" is a required Yes/No
# listbox — answered "Yes" (the form blocks submit otherwise). The
# formField80DSARElement "I am a former/potential employee/contractor/customer
# of Kalibrate" options are optional and left unselected.
# Country geo-prefills to "United States"; State is an autocomplete combobox.
# Fields: firstName, lastName, address, address2, city, zip, email,
# requestDetails. Submission is gated by a distorted-text image CAPTCHA
# (captchaCode), not reCAPTCHA — filled completely, code left for manual entry.
# **CAPTCHA solution required**
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal-uk.onetrust.com/webform/6e95a345-1222-4957-a118-93d60494951b/390b0718-0304-49af-9629-7cb64a946019"

# "Object to Processing" and the combined delete/opt-out option both cover opt-out.
RIGHT_MAP = {
    "access": [("Right to Know/Access to Information", "access")],
    "opt_out_sale_share": [
        ("Object to Processing", "object"),
        ("Data Deletion/Opt-out/Do Not Sell", "delete_optout"),
    ],
    "delete": [("Data Deletion/Opt-out/Do Not Sell", "delete_optout")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def _field_value(field):
    res = await field.execute_script("return this.value;")
    try:
        return (res["result"]["result"]["value"] or "").strip()
    except (KeyError, TypeError):
        return ""


async def _select_autocomplete(tab, field_id, search_text):
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
            await asyncio.sleep(0.4)
            return True
    return False


async def submit_request(tab, right_label, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(7)

    if not await _click_listbox_option(tab, right_label):
        print(f"{super_scraper.OOPS} Request type '{right_label}' not found")
        return
    # "Have you read and consented to the Privacy Policy?" — required, must be Yes
    await _click_listbox_option(tab, "Yes")

    await _select_autocomplete(tab, "countryDSARElement", "United States")
    await asyncio.sleep(0.5)
    await _select_autocomplete(tab, "stateDSARElement", SuperScraper.STATE)

    for fid, value in [
        ("firstNameDSARElement", SuperScraper.FIRST_NAME),
        ("lastNameDSARElement", SuperScraper.LAST_NAME),
        ("addressDSARElement", SuperScraper.ADDRESS),
        ("cityDSARElement", SuperScraper.CITY),
        ("zipDSARElement", SuperScraper.ZIP_CODE),
        ("emailDSARElement", SuperScraper.EMAIL),
    ]:
        el = await tab.find(id=fid, raise_exc=False)
        if el:
            await el.type_text(value)
            await asyncio.sleep(0.2)

    details = await tab.find(id="requestDetailsDSARElement", raise_exc=False)
    if details:
        await details.type_text(
            f"I am a {SuperScraper.STATE} resident exercising my privacy rights. "
            f"Request: {right_label}."
        )

    time.sleep(0.5)
    submit_btn = await tab.find(id="dsar-webform-submit-button", raise_exc=False)
    if submit_btn:
        await submit_btn.scroll_into_view()
    await SuperScraper.screenshot(tab, f"resources/screenshots/kalibrate_dry_run_{label}.png")
    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right_label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        return

    print(f"\nForm filled for '{right_label}'. Solve the reCAPTCHA, click Submit,")
    print("then press Enter once the confirmation page appears...")
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{right_label}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{right_label}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    requests = [entry for code in codes for entry in RIGHT_MAP[code]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right_label, label in requests:
            await submit_request(tab, right_label, label, super_scraper)


asyncio.run(main())
