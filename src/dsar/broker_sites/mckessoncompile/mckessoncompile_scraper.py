# mckessoncompile.com — OneTrust DSAR webform
# (privacyportal.onetrust.com/webform). One submission total, covering every selected
# right: the form has a single "Select request type" chooser, so the broadest option
# ("Access") is chosen and the selected rights are spelled out in Request Details.
# Which rights run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# Rights stated in Request Details: access, list of third parties, opt-out, delete.
# A BotDetect image CAPTCHA (captchaCode) gates submit — the form is filled up to that
# point and left for a manual entry.  **CAPTCHA solution required**
#
# Page elements (keep this list current):
#   formField38DSARElement   "State of Residence*" autocomplete combobox -> STATE
#   role="option" "Myself"   "I am submitting a request on behalf of" -> "Myself"
#   input[aria-label~"I am a"]   "I am a (an)" autocomplete — candidate labels are tried in order
#   input[aria-label~"request type"]  "Select request type" autocomplete — types "Access", picks first match
#   emailDSARElement / firstNameDSARElement / lastNameDSARElement   Email / First / Last name
#   dateOfBirthDSARElement   required date picker (MM/DD/YYYY from .env DD/MM/YYYY)
#   phoneNumberDSARElement   Phone  (formField19DSARElement = optional 2nd phone, left blank)
#   addressDSARElement / cityDSARElement / zipDSARElement   Address / City / Zip
#   formField35DSARElement   second state combobox
#   requestDetailsDSARElement   Request Details textarea
#   aria-label "I certify under penalty of perjury..."   certification checkbox
#   captchaCode              BotDetect image CAPTCHA (manual)
#   Optional agent/correction document upload left blank.
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.constants import Key

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = (
    "https://privacyportal.onetrust.com/webform/"
    "599133ba-bafa-4e24-8173-6e59b6c96dab/1554ac76-9012-4a4d-8cd4-53776f517530"
)

STATE_COMBO = "formField38DSARElement"  # "State of Residence*"
ADDRESS_STATE_COMBO = "formField35DSARElement"  # second state combobox
DETAILS_FIELD = "requestDetailsDSARElement"  # Request Details textarea
CERTIFY_LABEL = "I certify under penalty of perjury that the foregoing is true and correct."

# One request type ("Access") covers the whole combined submission; the rights themselves
# are stated in Request Details.
REQUEST_TYPE_TEXT = "Access"
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: REQUEST_TYPE_TEXT,
    Right.RIGHT_TO_LIST_OF_THIRD_PARTIES: REQUEST_TYPE_TEXT,
    Right.RIGHT_TO_OPT_OUT: REQUEST_TYPE_TEXT,
    Right.RIGHT_TO_DELETE: REQUEST_TYPE_TEXT,
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


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
    cur = await js_utils.js_eval(field, "return this.value")
    if cur and value.lower() not in str(cur).lower():
        print(f"{super_scraper.OOPS} combobox '{field_id}' value looks wrong: {cur!r}")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    details = SuperScraper.request_statement(rights, broker="McKesson Compile")

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(7)

        await _combo(tab, super_scraper, STATE_COMBO, SuperScraper.STATE)

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
                await js_utils.js_set_value(iama, candidate)
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
            await tab.keyboard.type_text(REQUEST_TYPE_TEXT)
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
            (DETAILS_FIELD, details),
        ):
            if not value:
                continue
            el = await tab.find(id=field_id, raise_exc=False)
            if el:
                await el.type_text(value)
                await asyncio.sleep(0.2)
            else:
                print(f"{super_scraper.OOPS} field '{field_id}' not found")

        await _combo(tab, super_scraper, ADDRESS_STATE_COMBO, SuperScraper.STATE)

        certify = await tab.find(
            **{"aria-label": CERTIFY_LABEL},
            raise_exc=False,
        )
        if certify:
            await certify.click_using_js()
        else:
            print(f"{super_scraper.OOPS} perjury-certification checkbox not found")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run_" + "_".join(r.value for r in rights))
        print(
            "Request filled but NOT submitted — enter the BotDetect image CAPTCHA "
            "(captchaCode) manually, then Submit."
        )


asyncio.run(main())
