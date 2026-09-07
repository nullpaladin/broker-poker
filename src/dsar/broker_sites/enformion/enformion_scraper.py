# enformion.com — exercises Opt-Out, Right to Know, Right to Correct,
# and Right to Delete (gated on REMOVE_INFORMATION).
# All four forms live on one page. reCAPTCHA Enterprise checkbox is required;
# checking it auto-submits the form via a JS callback — no separate submit click needed.
# Opt-Out and Delete send a verification email the user must click to complete.
# Know and Correct create a ticket directly.
import asyncio
import json
import time

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.enformion.com/opt-out/"

# (dropdown_value, label, has_extended_fields)
# "correct" form adds phone/address/city/state/zip/dob fields.
FORMS = [
    ("optOut",  "Do Not Sell / Right to Opt-out", False),
    ("access",  "Right to Know",                  False),
    ("correct", "Right to Correct",               True),
]
DELETE_FORM = ("delete", "Right to Delete", False)


def _js_set(selector, value):
    sel = json.dumps(selector)
    val = json.dumps(str(value))
    return (
        f"(function(){{"
        f"var el=document.querySelector({sel});"
        f"if(!el)return;"
        f"el.value={val};"
        f"el.dispatchEvent(new Event('input',{{bubbles:true}}));"
        f"el.dispatchEvent(new Event('change',{{bubbles:true}}));"
        f"}})();"
    )


def _js_check(selector):
    sel = json.dumps(selector)
    return (
        f"(function(){{"
        f"var el=document.querySelector({sel});"
        f"if(!el)return;"
        f"el.checked=true;"
        f"el.dispatchEvent(new Event('change',{{bubbles:true}}));"
        f"}})();"
    )


async def process_form(tab, dropdown_val, label, has_extended, super_scraper):
    form_sel = f'[data-value="{dropdown_val}"] .enf-zendesk-form'
    section_sel = f'[data-value="{dropdown_val}"]'

    # Reveal the section and sync the visible dropdown.
    await tab.execute_script(
        f"document.querySelector({json.dumps(section_sel)}).classList.remove('hidden');"
        f"document.querySelector('.rightsDropdown').value={json.dumps(dropdown_val)};"
    )

    # Delete form is gated by an exerciseRights select — choose "public" to reveal the form.
    if dropdown_val == "delete":
        await tab.execute_script(
            "var sel=document.getElementById('exerciseRights');"
            "sel.value='public';"
            "sel.dispatchEvent(new Event('change',{bubbles:true}));"
            "document.getElementById('publicContent').style.display='';"
        )
        time.sleep(0.5)

    # Base fields (requesterType already defaults to "subject").
    await tab.execute_script(_js_set(f'{form_sel} [name="firstName"]', SuperScraper.FIRST_NAME))
    await tab.execute_script(_js_set(f'{form_sel} [name="lastName"]', SuperScraper.LAST_NAME))
    await tab.execute_script(_js_set(f'{form_sel} [name="email"]', SuperScraper.EMAIL))
    await tab.execute_script(_js_check(f'{form_sel} [name="privacyAuthorization"]'))

    # Extended fields for the Correct form.
    if has_extended:
        state_abbrev = SuperScraper.STATE_ABBREVIATED
        if SuperScraper.PHONE_NUMBER:
            await tab.execute_script(_js_set(f'{form_sel} [name="phone"]', SuperScraper.PHONE_NUMBER))
        else:
            print(f"{super_scraper.OOPS} PHONE_NUMBER not set — Right to Correct form requires it")
        await tab.execute_script(_js_set(f'{form_sel} [name="address"]', SuperScraper.ADDRESS))
        await tab.execute_script(_js_set(f'{form_sel} [name="city"]', SuperScraper.CITY))
        await tab.execute_script(_js_set(f'{form_sel} [name="state"]', state_abbrev))
        await tab.execute_script(_js_set(f'{form_sel} [name="zip"]', SuperScraper.ZIP_CODE))
        # dob is optional; format must be YYYY-MM-DD (HTML date input).
        if SuperScraper.DATE_OF_BIRTH:
            await tab.execute_script(_js_set(f'{form_sel} [name="dob"]', SuperScraper.DATE_OF_BIRTH))

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        await asyncio.sleep(2)
        return

    print(f"\nForm ready: {label}")
    print("Solve the reCAPTCHA checkbox in the browser — it will auto-submit.")
    print("Press Enter after the confirmation page appears...")
    input()

    await asyncio.sleep(2)
    result = await tab.execute_script(
        "var c=document.querySelector('.enf-zendesk-form-cont'); return c ? c.innerText : '';"
    )
    if result and ("Email Sent" in result or "Submission Confirmation" in result):
        print(f"Submitted '{label}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation not detected — verify in browser before continuing")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    forms = list(FORMS)
    if SuperScraper.REMOVE_INFORMATION:
        forms.append(DELETE_FORM)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for dropdown_val, label, has_extended in forms:
            await tab.go_to(URL)
            await asyncio.sleep(5)  # wait for reCAPTCHA Enterprise to render
            await process_form(tab, dropdown_val, label, has_extended, super_scraper)


asyncio.run(main())
