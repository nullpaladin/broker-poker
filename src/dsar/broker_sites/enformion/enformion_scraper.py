# enformion.com — exercises Opt-Out, Right to Know and Right to Delete.
# All four forms (those three plus Right to Correct) live on one page. Right to Correct is
# not automatable and is not in RIGHT_MAP; its form additionally asks phone / address / city /
# state / zip / dob (name="phone", "address", "city", "state", "zip", "dob"). reCAPTCHA Enterprise checkbox is required;
# checking it auto-submits the form via a JS callback — no separate submit click needed.
# Opt-Out and Delete send a verification email the user must click to complete.
# Know and Correct create a ticket directly.
#
# Page elements (each form lives in [data-value="<dropdown value>"] .enf-zendesk-form):
#   .rightsDropdown                       "right" dropdown (values optOut / access / correct / delete)
#   [name="firstName"] / [name="lastName"] / [name="email"]   First / Last name / Email
#   [name="privacyAuthorization"]         privacy authorization checkbox
#   #exerciseRights (+ #publicContent)    Delete only: select set to "public" to reveal the form
#   reCAPTCHA Enterprise checkbox         auto-submits the form
#   .enf-zendesk-form-cont                result container read after submit
import asyncio
import json
import time

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://www.enformion.com/opt-out/"

# (dropdown_value, label)
RIGHT_MAP = {
    Right.RIGHT_TO_OPT_OUT: [("optOut", "Do Not Sell / Right to Opt-out")],
    Right.RIGHT_TO_ACCESS: [("access", "Right to Know")],
    Right.RIGHT_TO_DELETE: [("delete", "Right to Delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


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


async def process_form(tab, dropdown_val, label, right, super_scraper):
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

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right.name}' ({label}) for {SuperScraper.EMAIL}"
        )
        await asyncio.sleep(2)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
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
        print(f"Submitted '{right.name}' for {SuperScraper.EMAIL}")
    else:
        print(f"{super_scraper.OOPS} Confirmation not detected — verify in browser before continuing")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    forms = [(right, entry) for right in rights for entry in RIGHT_MAP[right]]

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right, (dropdown_val, label) in forms:
            await tab.go_to(URL)
            await asyncio.sleep(5)  # wait for reCAPTCHA Enterprise to render
            await process_form(tab, dropdown_val, label, right, super_scraper)


asyncio.run(main())
