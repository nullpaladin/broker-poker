# gumgum.com — OneTrust DSAR webform (privacyportal.onetrust.com/webform).
#   subjectTypesDSARElement  "I am a (an)": Prospective Employee / Client /
#       Employee / Visitor / Other -> "Visitor" (closest to a generic
#       consumer/site user).
#   requestTypesDSARElement  "Select request type(s)" role="option" group.
#       Treated as single-select — one submission per right (picking a second
#       option on this OneTrust build deselects the first): "Info Request"
#       (Access), "Opt out", "Do Not Sell", "Data Portability" unconditionally;
#       "Data Deletion" gated on REMOVE_INFORMATION. Other options
#       (Update Data / Object to Processing / File a Complaint / Review
#       Automated Decision / Restrict Processing) skipped as non-core.
#   countryDSARElement  autocomplete combobox -> United States
#   firstNameDSARElement / lastNameDSARElement / emailDSARElement
#   requestDetailsDSARElement left blank.
# reCAPTCHA gates submit — filled to that point.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = (
    "https://privacyportal.onetrust.com/webform/"
    "fbe4d6b4-7f02-4251-bc4b-142d5109ae3e/1683277a-0ae1-47dd-8845-5e811a07e307"
)

RIGHTS = [
    ("Info Request", "access"),
    ("Opt out", "opt_out"),
    ("Do Not Sell", "do_not_sell"),
    ("Data Portability", "portability"),
]
DELETE_RIGHT = ("Data Deletion", "delete")


async def _combo(tab, super_scraper, field_id, value):
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        print(f"{super_scraper.OOPS} combobox '{field_id}' not found")
        return
    await field.click()
    await asyncio.sleep(0.3)
    # Type only a short prefix, then click the exact role="option". Typing the
    # full value makes some OneTrust vt-autocomplete builds type-ahead-complete
    # it AND keep the typed text, doubling the value ("United StatesUnited
    # States"); a short ambiguous prefix does not trigger that.
    await tab.keyboard.type_text(value[:5])
    await asyncio.sleep(1.4)
    option = await tab.find(
        xpath=f"//*[@role='option' and normalize-space()={value!r}]", raise_exc=False
    )
    if option:
        await option.click()
    else:
        await tab.keyboard.type_text(value[5:])
        await asyncio.sleep(0.8)
        await tab.keyboard.press(Key.ARROWDOWN)
        await asyncio.sleep(0.3)
        await tab.keyboard.press(Key.ENTER)
    await asyncio.sleep(0.5)
    current = await field.execute_script("return this.value")
    cur = current.get("result", {}).get("result", {}).get("value") if isinstance(current, dict) else current
    if cur and value.lower() not in str(cur).lower():
        print(f"{super_scraper.OOPS} combobox '{field_id}' value looks wrong: {cur!r}")


async def _pick(tab, super_scraper, label):
    opt = await tab.find(**{"aria-label": label}, raise_exc=False)
    if not opt:
        opt = await tab.find(
            xpath=f"//*[@role='option' and normalize-space()={label!r}]", raise_exc=False
        )
    if opt:
        await opt.click_using_js()
        await asyncio.sleep(0.4)
    else:
        print(f"{super_scraper.OOPS} option {label!r} not found")


async def submit_request(tab, right_label, tag, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(7)

    await _pick(tab, super_scraper, "Visitor")
    await _pick(tab, super_scraper, right_label)
    await _combo(tab, super_scraper, "countryDSARElement", "United States")
    await asyncio.sleep(1)
    # A "State" field and a required "Request Details" textarea cascade in after
    # Country / the request type are set (not present in the DOM before that).
    await _combo(tab, super_scraper, "stateDSARElement", SuperScraper.STATE)

    for field_id, value in (
        ("firstNameDSARElement", SuperScraper.FIRST_NAME),
        ("lastNameDSARElement", SuperScraper.LAST_NAME),
        ("emailDSARElement", SuperScraper.EMAIL),
        (
            "requestDetailsDSARElement",
            f"I am exercising my '{right_label}' right with respect to the personal "
            "information GumGum holds about me.",
        ),
    ):
        el = await tab.find(id=field_id, raise_exc=False)
        if el:
            await el.type_text(value)
            await asyncio.sleep(0.2)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/gumgum_dry_run_{tag}.png", beyond_viewport=True)
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
