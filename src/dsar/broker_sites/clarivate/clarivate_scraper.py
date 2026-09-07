# clarivate.com — single general DSAR request form (no per-right-type picker).
# OneTrust Angular portal. Country of Residence is an autocomplete combobox —
# must type then click the dropdown option; setting .value alone is insufficient.
# reCAPTCHA v2 requires manual user solve before submit.
import asyncio
import json

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://privacyportal.onetrust.com/webform/7636e208-dda4-4218-8026-e1bc155873fc/ae937376-9b21-4996-9327-81eaaa1b20f9"


def _js_set(selector, value):
    sel = json.dumps(selector)
    val = json.dumps(str(value))
    return (
        f"(function(){{"
        f"var el=document.querySelector({sel});"
        f"if(!el)return;"
        f"el.value={val};"
        f"el.dispatchEvent(new Event('input',{{bubbles:true}}));"
        f"el.dispatchEvent(new Event('change',{{bubbles:true}}));"
        f"}})();"
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        # Select "Myself"
        await tab.execute_script(
            "document.querySelector('[aria-label=\"Myself\"]').click();"
        )

        # Country autocomplete — must type then select from dropdown
        country_input = await tab.find(
            xpath="//input[@id='countryDSARElement']",
            timeout=10,
            raise_exc=False,
        )
        if not country_input:
            print(f"{super_scraper.OOPS} Country input not found")
            return
        await country_input.click()
        await tab.keyboard.type_text("United States")
        await asyncio.sleep(2)
        clicked = await tab.execute_script(
            "var opts = Array.from(document.querySelectorAll('[role=option]'));"
            "var opt = opts.find(o => o.innerText.trim() === 'United States' && o.offsetParent !== null);"
            "if (opt) { opt.click(); return true; } return false;"
        )
        if not clicked:
            print(f"{super_scraper.OOPS} 'United States' option not found in country dropdown")

        await asyncio.sleep(1)

        # State autocomplete — appears dynamically after selecting United States
        state_input = await tab.find(
            xpath="//input[@id='stateDSARElement']",
            timeout=8,
            raise_exc=False,
        )
        if state_input:
            await state_input.click()
            await tab.keyboard.type_text(SuperScraper.STATE)
            await asyncio.sleep(2)
            state_name = json.dumps(SuperScraper.STATE)
            clicked = await tab.execute_script(
                f"var opts = Array.from(document.querySelectorAll('[role=option]'));"
                f"var opt = opts.find(o => o.innerText.trim() === {state_name} && o.offsetParent !== null);"
                f"if (opt) {{ opt.click(); return true; }} return false;"
            )
            if not clicked:
                print(f"{super_scraper.OOPS} State option '{SuperScraper.STATE}' not found in dropdown")
        else:
            print(f"{super_scraper.OOPS} State field not found — may not be required for this country")

        await asyncio.sleep(1)

        # Subject type autocomplete — "This request is for:" (data subject role, not DSAR right type).
        # "Customer" is the most applicable category for a general data broker DSAR.
        subject_input = await tab.find(
            xpath="//input[@id='subjectTypesDSARElement']",
            timeout=8,
            raise_exc=False,
        )
        if subject_input:
            await subject_input.click()
            await tab.keyboard.type_text("Customer")
            await asyncio.sleep(2)
            clicked = await tab.execute_script(
                "var opts = Array.from(document.querySelectorAll('[role=option]'));"
                "var opt = opts.find(o => o.innerText.trim() === 'Customer' && o.offsetParent !== null);"
                "if (opt) { opt.click(); return true; } return false;"
            )
            if not clicked:
                print(f"{super_scraper.OOPS} 'Customer' option not found in subject type dropdown")
        else:
            print(f"{super_scraper.OOPS} Subject type field not found")

        await asyncio.sleep(1)

        # Name fields
        await tab.execute_script(_js_set("#firstNameDSARElement", SuperScraper.FIRST_NAME))
        await tab.execute_script(_js_set("#lastNameDSARElement", SuperScraper.LAST_NAME))

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit DSAR for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}"
            )
            await asyncio.sleep(2)
            await SuperScraper.screenshot(tab, "resources/screenshots/clarivate_dry_run.png")
            return

        print(f"\nForm filled for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}.")
        print("Solve the reCAPTCHA in the browser, then click Submit.")
        print("Press Enter after submission completes...")
        input()

        result = await tab.execute_script("return document.body.innerText") or ""
        if any(w in result.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
            print(f"Submitted DSAR for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        else:
            print(f"{super_scraper.OOPS} Confirmation unclear — verify in browser")


asyncio.run(main())
