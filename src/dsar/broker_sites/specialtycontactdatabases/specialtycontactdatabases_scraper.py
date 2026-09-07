# specialtycontactdatabases.com — /do-not-sell/ Gravity Forms (form id 2),
# server-rendered, POSTs in place. One submission per right, chosen via the
# "input_7" radio group:
#   - "Request to Know ..."  -> Access  (unconditional)
#   - "Do Not Sell My Info ..." -> Opt-Out (unconditional)
#   - "Delete My Info ..."   -> Delete   (gated on REMOVE_INFORMATION)
# Fields (GF renders name='input_N' as id='input_2_N', name='input_6.1' as
# id='input_2_6_1'): first input_2_3_3, last input_2_3_6, email input_2_4,
# phone input_2_5, street input_2_6_1, line2 input_2_6_2, city input_2_6_3,
# state (plain text) input_2_6_4, zip input_2_6_5, country <select> input_2_6_6.
# Ends in a Gravity Forms reCAPTCHA v2 checkbox — every other field is filled
# and the form is left for a manual solve + Submit.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://specialtycontactdatabases.com/do-not-sell/"

RIGHTS = [
    ("Request to Know", "access"),
    ("Do Not Sell My Info", "opt_out"),
]
DELETE_RIGHT = ("Delete My Info", "delete")


async def _select_by_text(select_element, text):
    await select_element.execute_script(
        "for (var i=0;i<this.options.length;i++){"
        f"  if(this.options[i].text==={text!r}){{ this.selectedIndex=i; }}"
        "}"
        "this.dispatchEvent(new Event('change', {bubbles:true}));"
    )


async def submit_request(tab, value_prefix, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    radio = await tab.find(
        xpath=f"//input[@name='input_7' and starts-with(@value, {value_prefix!r})]", raise_exc=False
    )
    if not radio:
        print(f"{super_scraper.OOPS} request-type radio {value_prefix!r} not found")
        return
    await radio.click()
    await asyncio.sleep(0.5)

    fields = {
        "input_2_3_3": SuperScraper.FIRST_NAME,
        "input_2_3_6": SuperScraper.LAST_NAME,
        "input_2_4": SuperScraper.EMAIL,
        "input_2_5": SuperScraper.PHONE_NUMBER,
        "input_2_6_1": SuperScraper.ADDRESS,
        "input_2_6_2": SuperScraper.ADDRESS_LINE_TWO,
        "input_2_6_3": SuperScraper.CITY,
        "input_2_6_4": SuperScraper.STATE,
        "input_2_6_5": SuperScraper.ZIP_CODE,
    }
    for field_id, val in fields.items():
        if not val:
            continue
        el = await tab.find(id=field_id, raise_exc=False)
        if el:
            await el.type_text(val)
            await asyncio.sleep(0.15)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    country = await tab.find(id="input_2_6_6", raise_exc=False)
    if country:
        await _select_by_text(country, "United States")

    await asyncio.sleep(1)
    await tab.take_screenshot(path=f"resources/screenshots/specialtycontactdatabases_dry_run_{label}.png")
    print(f"Screenshot saved to resources/screenshots/specialtycontactdatabases_dry_run_{label}.png")
    print(
        f"'{value_prefix}' request filled but NOT submitted — a reCAPTCHA v2 "
        f"checkbox must be solved manually before Submit."
    )


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
        for value_prefix, label in rights:
            await submit_request(tab, value_prefix, label, super_scraper)


asyncio.run(main())
