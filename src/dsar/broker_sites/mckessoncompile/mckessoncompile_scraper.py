# mckessoncompile.com — OneTrust DSAR webform
# (privacyportal.onetrust.com/webform). One submission total.
#   formField38DSARElement  "State of Residence*" autocomplete combobox -> STATE
#   "I am submitting a request on behalf of"  role="option" pair -> "Myself"
#   "Select request type"  autocomplete combobox — the specific right; the
#       broadest available option is chosen ("Access Request" style) and every
#       other right is also stated in Request Details, since this build offers
#       no multi-select. If the guessed option label does not match, the field
#       is left for manual completion (a warning is printed).
#   emailDSARElement / firstNameDSARElement / lastNameDSARElement
#   dateOfBirthDSARElement  required date picker (MM/DD/YYYY from .env DD/MM/YYYY)
#   phoneNumberDSARElement  (formField19DSARElement = optional 2nd phone, blank)
#   addressDSARElement / cityDSARElement / formField35DSARElement (state combo) /
#       zipDSARElement
#   requestDetailsDSARElement  the rights being exercised, in words
#   formField13DSARElement  "I certify under penalty of perjury..." checkbox
#   Optional agent/correction document upload left blank.
# A BotDetect image CAPTCHA (captchaCode) gates submit — filled to that point.
# **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = (
    "https://privacyportal.onetrust.com/webform/"
    "599133ba-bafa-4e24-8173-6e59b6c96dab/1554ac76-9012-4a4d-8cd4-53776f517530"
)

RIGHTS_TEXT_BASE = (
    "I am exercising my applicable state privacy rights: the right to know/access "
    "the personal information you have about me, the right to a list of the "
    "categories of third parties to whom you have disclosed my personal "
    "information, and the right to opt out of the sale or sharing of my personal "
    "information and its processing for targeted advertising."
)
RIGHTS_TEXT_DELETE = " I also request deletion of my personal information."


def _dob_mm_dd_yyyy():
    if not SuperScraper.DATE_OF_BIRTH:
        return ""
    parts = SuperScraper.DATE_OF_BIRTH.split("/")
    if len(parts) != 3:
        return SuperScraper.DATE_OF_BIRTH
    day, month, year = parts
    return f"{month}/{day}/{year}"


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


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,3400")

    details = RIGHTS_TEXT_BASE + (RIGHTS_TEXT_DELETE if SuperScraper.REMOVE_INFORMATION else "")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(7)

        await _combo(tab, super_scraper, "formField38DSARElement", SuperScraper.STATE)

        # "I am submitting a request on behalf of" -> Myself
        myself = await tab.find(**{"aria-label": "Myself"}, raise_exc=False)
        if not myself:
            myself = await tab.find(
                xpath="//*[@role='option' and normalize-space()='Myself']", raise_exc=False
            )
        if myself:
            await myself.click_using_js()
            await asyncio.sleep(0.4)
        else:
            print(f"{super_scraper.OOPS} 'Myself' (on behalf of) option not found")

        # A separate required "I am a (an)" autocomplete — try common labels.
        iama = await tab.find(
            xpath="//input[contains(@aria-label,'I am a')]", raise_exc=False
        )
        if iama:
            picked = False
            for candidate in ("Consumer", "Individual", "Customer", "Patient", "Other"):
                await iama.click()
                await asyncio.sleep(0.3)
                await iama.execute_script(
                    "var s=Object.getOwnPropertyDescriptor(Object.getPrototypeOf(this),'value').set;"
                    f"s.call(this,{candidate!r});"
                    "this.dispatchEvent(new Event('input',{bubbles:true}));"
                )
                await asyncio.sleep(1)
                opt = await tab.find(
                    xpath=f"//*[@role='option' and normalize-space()={candidate!r}]", raise_exc=False
                )
                if opt:
                    await opt.click()
                    picked = True
                    break
            if not picked:
                print(
                    f"{super_scraper.OOPS} 'I am a (an)' — no common option matched; "
                    "select it manually before submitting."
                )
        await asyncio.sleep(0.3)

        # "Select request type" autocomplete — try common OneTrust labels.
        rt_input = await tab.find(
            xpath="//input[contains(@aria-label,'request type') or contains(@aria-label,'Request Type') or contains(@aria-label,'Select request type')]",
            raise_exc=False,
        )
        if rt_input:
            await rt_input.click()
            await asyncio.sleep(0.4)
            await tab.keyboard.type_text("Access")
            await asyncio.sleep(1.4)
            await tab.keyboard.press(Key.ARROWDOWN)
            await asyncio.sleep(0.3)
            await tab.keyboard.press(Key.ENTER)
            await asyncio.sleep(0.5)
        else:
            print(
                f"{super_scraper.OOPS} 'Select request type' field not found — "
                "complete it manually before submitting."
            )

        for field_id, value in (
            ("emailDSARElement", SuperScraper.EMAIL),
            ("firstNameDSARElement", SuperScraper.FIRST_NAME),
            ("lastNameDSARElement", SuperScraper.LAST_NAME),
            ("dateOfBirthDSARElement", _dob_mm_dd_yyyy()),
            ("phoneNumberDSARElement", SuperScraper.PHONE_NUMBER),
            ("addressDSARElement", SuperScraper.ADDRESS),
            ("cityDSARElement", SuperScraper.CITY),
            ("zipDSARElement", SuperScraper.ZIP_CODE),
            ("requestDetailsDSARElement", details),
        ):
            if not value:
                continue
            el = await tab.find(id=field_id, raise_exc=False)
            if el:
                await el.type_text(value)
                await asyncio.sleep(0.2)
            else:
                print(f"{super_scraper.OOPS} field '{field_id}' not found")

        await _combo(tab, super_scraper, "formField35DSARElement", SuperScraper.STATE)

        certify = await tab.find(
            **{"aria-label": "I certify under penalty of perjury that the foregoing is true and correct."},
            raise_exc=False,
        )
        if certify:
            await certify.click_using_js()
        else:
            print(f"{super_scraper.OOPS} perjury-certification checkbox not found")

        await asyncio.sleep(1)
        await tab.take_screenshot(
            path="resources/screenshots/mckessoncompile_dry_run.png", beyond_viewport=True
        )
        print("Screenshot saved to resources/screenshots/mckessoncompile_dry_run.png")
        print(
            "Request filled but NOT submitted — enter the BotDetect image CAPTCHA "
            "(captchaCode) manually, then Submit."
        )


asyncio.run(main())
