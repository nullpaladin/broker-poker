# spectrummailinglists.com — the Right to Opt-Out is an embedded Google Form
# (navigated to directly). Every other request type is declined with a
# public-records excuse, so this scraper only exercises Opt-Out.
# Questions:
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
import re

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

FORM_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLSeOxYNRRsFd1SBrN7LZZgSNrS2YJX00VhvdiUVTcrUgmW_8Xw/viewform"
)

_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}


def _num(token):
    token = token.strip().lower()
    return _WORDS.get(token, int(token) if token.lstrip("-").isdigit() else None)


def solve_arithmetic(question):
    m = re.search(r"([\w-]+)\s*(plus|minus|\+|-|times|multiplied by|x)\s*([\w-]+)", question, re.I)
    if not m:
        return None
    a, op, b = _num(m.group(1)), m.group(2).lower(), _num(m.group(3))
    if a is None or b is None:
        return None
    if op in ("plus", "+"):
        return str(a + b)
    if op in ("minus", "-"):
        return str(a - b)
    return str(a * b)


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
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

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
        raw = await tab.execute_script(
            "var li=[...document.querySelectorAll('div[role=listitem]')];"
            "li=li[li.length-1];"
            "return li ? li.innerText : '';"
        )
        q_text = raw.get("result", {}).get("result", {}).get("value") if isinstance(raw, dict) else raw
        answer = solve_arithmetic(q_text or "")
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

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/spectrummailinglists_dry_run.png", beyond_viewport=True)
        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit opt-out for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}"
            )
            return

        submit = await tab.find(
            xpath="//div[@role='button']//span[normalize-space(.)='Submit']", raise_exc=False
        )
        if submit:
            await submit.click()
            await asyncio.sleep(4)
            print(f"Submitted opt-out for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")


asyncio.run(main())
