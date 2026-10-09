# carfax.com — /company/consumer-privacy/ "CARFAX Consumer Privacy Request
# Form", a custom React multi-step form. Selecting a "State of Residence"
# (<select name="state">) progressively reveals the request-type radios, and
# picking a radio reveals the identity fields — all on one page (no navigation).
#
# One submission per requestTypeInput radio (single-select):
#   "I want to know what personal information CARFAX has about me"  -> Access
#   "I want to correct the personal information ..."                -> Correct (skipped)
#   "I want to have my personal information deleted ..."            -> Delete
#       (gated on REMOVE_INFORMATION)
# Fields (stable `textInput-userInput-<name>-input` ids): firstName, lastName,
# email, confirmEmail (both = EMAIL), phone. A required "By submitting this
# request, you are confirming ..." attestation checkbox is checked.
# reCAPTCHA v2 gates submit — filled to that point.
# **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://www.carfax.com/company/consumer-privacy/"

RIGHTS = [("I want to know what personal information CARFAX has about me", "access")]
DELETE_RIGHT = ("I want to have my personal information deleted", "delete")


async def submit_request(tab, radio_label, tag, super_scraper):
    try:
        await tab.go_to(URL)
    except Exception as exc:
        print(f"(carfax: go_to reported {exc!r} — continuing)")
    await asyncio.sleep(9)

    state_abbr = await SuperScraper.state_full_name_to_abbreviated(SuperScraper.STATE)
    state_select = await tab.find(id="selectInput-userInput-state-input", raise_exc=False)
    if state_select:
        await state_select.execute_script(
            "for (var i=0;i<this.options.length;i++){"
            f"  if(this.options[i].value==={state_abbr!r}){{ this.selectedIndex=i; }}"
            "}"
            "this.dispatchEvent(new Event('change', {bubbles:true}));"
        )
        await asyncio.sleep(2)
    else:
        print(f"{super_scraper.OOPS} state select not found")

    # The radio lives inside its <label>; click the label (clicking the bare
    # <input> via pydoll doesn't fire React's onChange, so the identity fields
    # never cascade in).
    radio_label_el = await tab.find(
        xpath=f"//label[.//input[@name='requestTypeInput']][contains(normalize-space(), {radio_label!r})]",
        raise_exc=False,
    )
    if not radio_label_el:
        radio_label_el = await tab.find(
            xpath=f"//*[contains(normalize-space(), {radio_label!r})]"
            f"/ancestor-or-self::label[.//input[@name='requestTypeInput']][1]",
            raise_exc=False,
        )
    if radio_label_el:
        await radio_label_el.click()
        await asyncio.sleep(3)
    else:
        print(f"{super_scraper.OOPS} request-type radio {radio_label!r} not found")

    for field_id, value in (
        ("textInput-userInput-firstName-input", SuperScraper.FIRST_NAME),
        ("textInput-userInput-lastName-input", SuperScraper.LAST_NAME),
        ("textInput-userInput-email-input", SuperScraper.EMAIL),
        ("textInput-userInput-confirmEmail-input", SuperScraper.EMAIL),
        ("textInput-userInput-phone-input", SuperScraper.PHONE_NUMBER),
    ):
        if not value:
            continue
        el = await tab.find(id=field_id, raise_exc=False)
        if el:
            await el.type_text(value)
            await asyncio.sleep(0.2)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    attest = await tab.find(
        xpath="//input[@type='checkbox' and @name='cfx-checkmark']", raise_exc=False
    )
    if not attest:
        attest = await tab.find(
            xpath="//label[contains(normalize-space(), 'By submitting this request')]//input[@type='checkbox']",
            raise_exc=False,
        )
    if attest:
        await attest.click()
    else:
        print(f"{super_scraper.OOPS} attestation checkbox not found")

    await asyncio.sleep(1)
    await tab.take_screenshot(path=f"resources/screenshots/carfax_dry_run_{tag}.png", beyond_viewport=True)
    print(f"Screenshot saved to resources/screenshots/carfax_dry_run_{tag}.png")
    print(f"'{radio_label}' filled but NOT submitted — solve the reCAPTCHA manually, then Submit.")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,3000")

    rights = list(RIGHTS)
    if SuperScraper.REMOVE_INFORMATION:
        rights.append(DELETE_RIGHT)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for radio_label, tag in rights:
            await submit_request(tab, radio_label, tag, super_scraper)


asyncio.run(main())
