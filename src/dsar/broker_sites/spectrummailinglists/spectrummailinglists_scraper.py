# spectrummailinglists.com — the Right to Opt-Out is an embedded Google Form
# (navigated to directly). Every other request type is declined with a
# public-records excuse, so this scraper only exercises Opt-Out (RIGHT_MAP has a
# single entry; the run is skipped unless an opt-out right is requested via
# SuperScraper.rights_to_exercise).
# Page elements (Google Form questions):
#   [radio]    "I am submitting this request:" -> "For myself, my family member
#              or similar"
#   [short]    First Name, Last Name, City, Zip Code
#   [para]     "Mailing Street Address (including apartment number ...)"
#   [dropdown] "State" (2-letter abbreviations)
#   [short]    a static arithmetic question ("What is 6 minus 1?") acting as a
#              CAPTCHA — parsed and answered dynamically.
# Google Form text inputs have no aria-label -> reached via a role="listitem"-
# scoped xpath. Radio uses aria-label. Dropdown is role="listbox"/"option".
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import captcha_solutions_util, js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

FORM_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLSeOxYNRRsFd1SBrN7LZZgSNrS2YJX00VhvdiUVTcrUgmW_8Xw/viewform"
)

# The only right the form honours (the Google Form has no per-right choice).
RIGHT_MAP = {Right.RIGHT_TO_OPT_OUT: "opt-out"}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (A fixed-purpose opt-out Google Form; its heading selector is unrecorded.)

FIELD_XPATHS = {
    "First Name": "//div[@role='listitem'][.//span[contains(normalize-space(.), 'First Name')]]//input",
    "Last Name": "//div[@role='listitem'][.//span[contains(normalize-space(.), 'Last Name')]]//input",
    "Mailing Street Address": "//div[@role='listitem'][.//span[contains(normalize-space(.), 'Mailing Street Address')]]//textarea",
    "City": "//div[@role='listitem'][.//span[contains(normalize-space(.), 'City')]]//input",
    "Zip Code": "//div[@role='listitem'][.//span[contains(normalize-space(.), 'Zip Code')]]//input",
}


async def fill_text(tab, super_scraper, question, value, para=False):
    if not value:
        return
    tag = "textarea" if para else "input"
    xpath = f"//div[@role='listitem'][.//span[contains(normalize-space(.), {question!r})]]//{tag}"
    field = await tab.find(xpath=xpath, raise_exc=False)
    if not field:
        print(f"{super_scraper.OOPS} field for {question!r} not found")
        return
    await field.click()
    await tab.keyboard.type_text(text=value)
    await asyncio.sleep(0.3)


async def main():
    super_scraper = SuperScraper()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(FORM_URL)
        await asyncio.sleep(5)

        myself = await tab.find(
            xpath="//div[@role='radio'][contains(@aria-label,'For myself')]", raise_exc=False
        )
        if myself:
            await myself.click()
            await asyncio.sleep(0.4)
        else:
            print(f"{super_scraper.OOPS} 'For myself' radio not found")

        await fill_text(tab, super_scraper, "First Name", SuperScraper.FIRST_NAME)
        await fill_text(tab, super_scraper, "Last Name", SuperScraper.LAST_NAME)
        await fill_text(tab, super_scraper, "Mailing Street Address", SuperScraper.ADDRESS, para=True)
        await fill_text(tab, super_scraper, "City", SuperScraper.CITY)
        await fill_text(tab, super_scraper, "Zip Code", SuperScraper.ZIP_CODE)

        state_abbr = SuperScraper.STATE_ABBREVIATED
        listbox = await tab.find(
            xpath="//div[@role='listitem'][.//span[contains(normalize-space(.), 'State')]]//div[@role='listbox']",
            raise_exc=False,
        )
        if listbox:
            await listbox.click()
            await asyncio.sleep(0.6)
            opt = await tab.find(
                xpath=f"//div[@role='option']//span[normalize-space(.)={state_abbr!r}]", raise_exc=False
            )
            if opt:
                await opt.click()
            else:
                print(f"{super_scraper.OOPS} state option {state_abbr!r} not found")
        else:
            print(f"{super_scraper.OOPS} state dropdown not found")
        await asyncio.sleep(0.4)

        # Arithmetic anti-bot question — it is the last question on the form.
        q_text = await js_utils.js_eval(
            tab,
            "var li=[...document.querySelectorAll('div[role=listitem]')];"
            "li=li[li.length-1];"
            "return li ? li.innerText : '';",
        )
        answer = captcha_solutions_util.solve_math_captcha(q_text or "")
        if answer is not None:
            # The math answer is the last short-text input on the form. It needs
            # a scroll_into_view + settle before typing — Google Forms otherwise
            # drops the keystrokes when focus was just moved off the State
            # dropdown.
            field = await tab.find(
                xpath='(//input[@jsname="YPqjbf" and @type="text"])[last()]', raise_exc=False
            )
            if field:
                await field.scroll_into_view()
                await asyncio.sleep(0.4)
                await field.click()
                await asyncio.sleep(0.5)
                await field.type_text(answer)
                await asyncio.sleep(0.3)
            else:
                print(f"{super_scraper.OOPS} arithmetic answer field not found")
        else:
            print(f"{super_scraper.OOPS} could not parse arithmetic question: {q_text!r}")

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run_opt_out")
        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit '{Right.RIGHT_TO_OPT_OUT.name}' for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}"
            )
            return

        submit = await tab.find(
            xpath="//div[@role='button']//span[normalize-space(.)='Submit']", raise_exc=False
        )
        if submit:
            await submit.click()
            await asyncio.sleep(4)
            print(
                f"Submitted '{Right.RIGHT_TO_OPT_OUT.name}' for {SuperScraper.FIRST_NAME} "
                f"{SuperScraper.LAST_NAME} — confirm in the browser."
            )


asyncio.run(main())
