# propstream.com — OneTrust DSAR webform (privacyportal.onetrust.com/webform).
#   formField81DSARElement  "I am a" autocomplete — options unknown, so common
#       labels are tried ("Consumer"/"Individual"/...); if none match it is left
#       for manual completion (a warning is printed).
#   "Who are you submitting this request for?"  role="option" pair -> "Myself"
#   "Select Right to Exercise"  role="option" group that cascades in after "I am
#       a" is set. Treated as single-select — one submission per right:
#       "Request a copy of my personal information" (Access) + "Request to
#       opt-out of sale and sharing" + "Request to know about categories of
#       information maintained by PropStream" unconditionally; "Request to
#       delete" gated on REMOVE_INFORMATION; "Request to correct" skipped.
#   formField78DSARElement  "Have you made a similar request to PropStream in
#       the past 12 months?" role="listbox" -> "No"
#   countryDSARElement  combobox -> United States; a "state of residency"
#       combobox then cascades in and is filled from the persona if present.
#   firstNameDSARElement / lastNameDSARElement / emailDSARElement
# (Public-servant "Daniel's Law" redaction requests are a separate email flow to
#  redactionrequest@propstream.com — out of scope here.)
# reCAPTCHA gates submit — filled to that point.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = (
    "https://privacyportal.onetrust.com/webform/"
    "23dbbccc-a76c-4410-a68e-f247d70e566c/7d013624-d2db-430a-9265-3112f7c4177c"
)

RIGHTS = [
    ("Request a copy of my personal information", "access"),
    ("Request to opt-out of sale and sharing", "opt_out"),
    ("Request to know about categories of information maintained by PropStream", "categories"),
]
DELETE_RIGHT = ("Request to delete", "delete")

IAM_CANDIDATES = ("Consumer", "Individual", "Customer", "Member of the public", "A consumer", "Other")


async def _combo(tab, super_scraper, field_id, value):
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        print(f"{super_scraper.OOPS} combobox '{field_id}' not found")
        return
    await field.click()
    await asyncio.sleep(0.3)
    await field.execute_script(
        "var s=Object.getOwnPropertyDescriptor(Object.getPrototypeOf(this),'value').set;"
        f"s.call(this,{value!r});"
        "this.dispatchEvent(new Event('input',{bubbles:true}));"
    )
    await asyncio.sleep(1.3)
    opt = await tab.find(xpath=f"//*[@role='option' and normalize-space()={value!r}]", raise_exc=False)
    if opt:
        await opt.click()
    else:
        await tab.keyboard.press(Key.ENTER)
    await asyncio.sleep(0.4)
    current = await field.execute_script("return this.value")
    cur = current.get("result", {}).get("result", {}).get("value") if isinstance(current, dict) else current
    if str(cur or "").strip().lower() != value.lower():
        await field.execute_script(
            "var s=Object.getOwnPropertyDescriptor(Object.getPrototypeOf(this),'value').set;"
            f"s.call(this,{value!r});"
            "this.dispatchEvent(new Event('input',{bubbles:true}));"
            "this.dispatchEvent(new Event('change',{bubbles:true}));"
            "this.dispatchEvent(new Event('blur',{bubbles:true}));"
        )


async def _pick(tab, super_scraper, label):
    opt = await tab.find(**{"aria-label": label}, raise_exc=False)
    if not opt:
        opt = await tab.find(xpath=f"//*[@role='option' and normalize-space()={label!r}]", raise_exc=False)
    if opt:
        await opt.click_using_js()
        await asyncio.sleep(0.4)
        return True
    return False


async def _pick_iam(tab, super_scraper):
    iam = await tab.find(id="formField81DSARElement", raise_exc=False)
    if not iam:
        print(f"{super_scraper.OOPS} 'I am a' field not found")
        return
    for cand in IAM_CANDIDATES:
        await iam.click()
        await asyncio.sleep(0.3)
        await iam.execute_script(
            "var s=Object.getOwnPropertyDescriptor(Object.getPrototypeOf(this),'value').set;"
            f"s.call(this,{cand!r});"
            "this.dispatchEvent(new Event('input',{bubbles:true}));"
        )
        await asyncio.sleep(1)
        opt = await tab.find(xpath=f"//*[@role='option' and normalize-space()={cand!r}]", raise_exc=False)
        if opt:
            await opt.click()
            return
    print(f"{super_scraper.OOPS} 'I am a' — no common option matched; complete it manually.")


async def submit_request(tab, right_label, tag, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(7)

    await _pick_iam(tab, super_scraper)
    await asyncio.sleep(0.5)
    await _pick(tab, super_scraper, "Myself")
    await asyncio.sleep(0.8)

    if not await _pick(tab, super_scraper, right_label):
        print(f"{super_scraper.OOPS} right '{right_label}' not found")
    await asyncio.sleep(1)

    # formField78DSARElement listbox — "similar request in the past 12 months?"
    no_opt = await tab.find(
        xpath="//div[@id='formField78DSARElement']//*[@role='option' and normalize-space()='No']",
        raise_exc=False,
    )
    if not no_opt:
        no_opt = await tab.find(xpath="//*[@role='option' and normalize-space()='No']", raise_exc=False)
    if no_opt:
        await no_opt.click_using_js()
        await asyncio.sleep(0.4)
    else:
        print(f"{super_scraper.OOPS} 'past 12 months' -> No option not found")

    await _combo(tab, super_scraper, "countryDSARElement", "United States")
    await asyncio.sleep(1)
    # A state-of-residency combobox cascades in after Country.
    state_field = await tab.find(id="stateDSARElement", raise_exc=False)
    if not state_field:
        state_field = await tab.find(
            xpath="//input[@role='combobox' and (contains(@aria-label,'state') or contains(@aria-label,'State'))]",
            raise_exc=False,
        )
    if state_field:
        state_id = state_field.get_attribute("id")
        if state_id:
            await _combo(tab, super_scraper, state_id, SuperScraper.STATE)

    for field_id, value in (
        ("firstNameDSARElement", SuperScraper.FIRST_NAME),
        ("lastNameDSARElement", SuperScraper.LAST_NAME),
        ("emailDSARElement", SuperScraper.EMAIL),
    ):
        el = await tab.find(id=field_id, raise_exc=False)
        if el:
            await el.type_text(value)
            await asyncio.sleep(0.2)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    await asyncio.sleep(1)
    await tab.take_screenshot(path=f"resources/screenshots/propstream_dry_run_{tag}.png", beyond_viewport=True)
    print(f"Screenshot saved to resources/screenshots/propstream_dry_run_{tag}.png")
    print(f"'{right_label}' filled but NOT submitted — solve the reCAPTCHA manually, then Submit.")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    rights = list(RIGHTS)
    if SuperScraper.REMOVE_INFORMATION:
        rights.append(DELETE_RIGHT)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right_label, tag in rights:
            await submit_request(tab, right_label, tag, super_scraper)


asyncio.run(main())
