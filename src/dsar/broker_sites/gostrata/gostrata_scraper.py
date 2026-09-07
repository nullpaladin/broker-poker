# gostrata.com — /do-not-sell-my-personal-information/ Gravity Forms (form id 5),
# server-rendered, POSTs in place. A single bundled request: the required
# certification checkbox reads "...you wish to have your personal information
# deleted and not sold", so this is Opt-Out + Delete combined with no separate
# Access path. Submitted unconditionally (it is the only mechanism the site
# offers).
#
# Quirks:
#  - The whole #gform_wrapper_5 ships with style="display:none" and is only
#    un-hidden by the page's own jQuery on ready; a Complianz cookie banner
#    ("Accept") sits in front of it. This scraper clicks Accept, then force-
#    un-hides the wrapper if it is still hidden, before filling.
#  - Every field starts with 0x0 layout, so type_text()'s visibility check
#    fails — values are set via the native input setter + input/change events
#    instead (the phone field also has a jQuery .mask('(999) 999-9999') that
#    reformats on the input event).
# Fields (GF id scheme: name='input_12.3' -> id='input_5_12_3'):
#   input_5_19  honeypot ("URL") — left blank
#   input_5_12_3 / input_5_12_6  first / last name
#   input_5_13_1 street, input_5_13_3 city, input_5_13_4 <select> state,
#   input_5_13_5 zip  (input_5_13_6 hidden country already "United States")
#   input_5_14 email, input_5_8 email confirmation, input_5_15 phone
#   input_5_16_1 required certification checkbox, input_5_17 comments (blank)
# Ends in a CAPTCHA (input_5_18) — filled to that point and left for a manual
# solve + Submit.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://www.gostrata.com/do-not-sell-my-personal-information/"

JS_SET = """
var el = document.getElementById(arguments0);
if (!el) return 'missing';
var proto = Object.getPrototypeOf(el);
var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
setter.call(el, arguments1);
el.dispatchEvent(new Event('input', {bubbles:true}));
el.dispatchEvent(new Event('change', {bubbles:true}));
return el.value;
"""


async def _js_set(tab, field_id, value):
    script = JS_SET.replace("arguments0", repr(field_id)).replace("arguments1", repr(value))
    return await tab.execute_script(script)


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        # Dismiss the Complianz cookie banner (may be absent/offscreen in
        # headless) — click it via JS rather than a visibility-gated .click().
        await tab.execute_script(
            "var b=document.querySelector('.cmplz-accept,.cmplz-btn.cmplz-accept');"
            "if(b){b.click();}"
        )
        await asyncio.sleep(2)

        # Un-hide the form wrapper if the page JS hasn't already.
        await tab.execute_script(
            "var w=document.getElementById('gform_wrapper_5');"
            "if(w){w.style.display='';w.removeAttribute('style');}"
            "var f=document.getElementById('gform_5'); if(f){f.style.opacity='';}"
        )
        await asyncio.sleep(1)

        text_fields = {
            "input_5_12_3": SuperScraper.FIRST_NAME,
            "input_5_12_6": SuperScraper.LAST_NAME,
            "input_5_13_1": SuperScraper.ADDRESS,
            "input_5_13_3": SuperScraper.CITY,
            "input_5_13_5": SuperScraper.ZIP_CODE,
            "input_5_14": SuperScraper.EMAIL,
            "input_5_8": SuperScraper.EMAIL,
            "input_5_15": SuperScraper.PHONE_NUMBER,
        }
        for field_id, val in text_fields.items():
            if not val:
                continue
            res = await _js_set(tab, field_id, val)
            got = res.get("result", {}).get("result", {}).get("value") if isinstance(res, dict) else res
            if got == "missing":
                print(f"{super_scraper.OOPS} field '{field_id}' not found")
            elif not got:
                print(f"{super_scraper.OOPS} field '{field_id}' set but read back empty")

        state = await tab.find(id="input_5_13_4", raise_exc=False)
        if state:
            await state.execute_script(
                "for (var i=0;i<this.options.length;i++){"
                f"  if(this.options[i].text==={SuperScraper.STATE!r}){{ this.selectedIndex=i; }}"
                "}"
                "this.dispatchEvent(new Event('change', {bubbles:true}));"
            )
        else:
            print(f"{super_scraper.OOPS} state <select> not found")

        cert = await tab.find(id="input_5_16_1", raise_exc=False)
        if cert:
            await cert.execute_script(
                "this.checked = true;"
                "this.dispatchEvent(new Event('click', {bubbles:true}));"
                "this.dispatchEvent(new Event('change', {bubbles:true}));"
            )
        else:
            print(f"{super_scraper.OOPS} certification checkbox not found")

        await asyncio.sleep(1)
        await tab.take_screenshot(path="resources/screenshots/gostrata_dry_run.png", beyond_viewport=True)
        print("Screenshot saved to resources/screenshots/gostrata_dry_run.png")
        print(
            "Opt-Out/Delete request filled but NOT submitted — solve the CAPTCHA "
            "(input_5_18) manually, then click Submit."
        )


asyncio.run(main())
