# penlink.com — /your-privacy-choices/ Gravity Forms (form 9), server-rendered.
# One submission per "Request Type" (input_9_33 <select>):
#   "Access my personal information / Port my personal information"       -> Access
#   "Opt out of sale or sharing of my personal information"              -> Opt-Out
#   "Request list of third parties to which personal information was
#    disclosed (Oregon and Minnesota only)"                             -> 3rd-parties
#       (offered because the .env persona's state is Minnesota)
#   "Delete my personal information"                                     -> Delete
#       (gated on REMOVE_INFORMATION)
#   Correct / Object / "Opt out of marketing" are skipped as non-core.
# Fields: input_9_1 first, input_9_10 last, input_9_2 email, input_9_23
#   Advertising ID, input_9_24_1..5 street/line2/city/state/zip, input_9_24_6
#   <select> country, input_25 radio -> "The consumer named above",
#   input_9_34 comments (blank).
# reCAPTCHA gates submit — filled to that point.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://www.penlink.com/your-privacy-choices/"

RIGHTS = [
    ("Access my personal information / Port my personal information", "access"),
    ("Opt out of sale or sharing of my personal information", "opt_out"),
    (
        "Request list of third parties to which personal information was disclosed "
        "(Oregon and Minnesota only)",
        "third_parties",
    ),
]
DELETE_RIGHT = ("Delete my personal information", "delete")


async def _select_by_text(select_element, text):
    await select_element.execute_script(
        "for (var i=0;i<this.options.length;i++){"
        f"  if(this.options[i].text.trim()==={text!r}){{ this.selectedIndex=i; }}"
        "}"
        "this.dispatchEvent(new Event('change', {bubbles:true}));"
    )


async def submit_request(tab, right_label, tag, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    rt = await tab.find(id="input_9_33", raise_exc=False)
    if rt:
        await _select_by_text(rt, right_label)
        await asyncio.sleep(0.5)
    else:
        print(f"{super_scraper.OOPS} request-type select not found")

    fields = {
        "input_9_1": SuperScraper.FIRST_NAME,
        "input_9_10": SuperScraper.LAST_NAME,
        "input_9_2": SuperScraper.EMAIL,
        "input_9_23": SuperScraper.ADVERTISING_ID,
        "input_9_24_1": SuperScraper.ADDRESS,
        "input_9_24_2": SuperScraper.ADDRESS_LINE_TWO,
        "input_9_24_3": SuperScraper.CITY,
        "input_9_24_4": SuperScraper.STATE,
        "input_9_24_5": SuperScraper.ZIP_CODE,
    }
    for field_id, val in fields.items():
        if not val:
            continue
        el = await tab.find(id=field_id, raise_exc=False)
        if el:
            await el.type_text(val)
            await asyncio.sleep(0.12)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    country = await tab.find(id="input_9_24_6", raise_exc=False)
    if country:
        await _select_by_text(country, "United States")

    consumer_radio = await tab.find(id="choice_9_25_0", raise_exc=False)
    if consumer_radio:
        await consumer_radio.click()

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/penlink_dry_run_{tag}.png", beyond_viewport=True)
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
