# lead411.com — your-privacy-choices/. "Request Type" select
# (`user_option_request_for_profile`) offers Access/Opt-out of Sale/Know
# What Is Processed/Correct/Delete/Port — one submission per type; Know/
# Correct/Port skipped as auxiliary (not core Access/Opt-Out/Delete
# rights). Selecting Country=United States reveals a State select
# (`us-states`, initially `display:none`). Email + a required "I Agree"
# checkbox + reCAPTCHA v2 checkbox gate the "Get Code" button, which emails
# a real verification code — a side-effect trigger, so this scraper fills
# the form and stops there regardless of DRY_RUN. A Cookiebot cookie-
# consent banner also offers its own one-click "Do not sell or share my
# personal information" button directly in the banner — dismissed via the
# main "OK" accept instead so it doesn't interfere with clicking through
# the actual form fields (that shortcut button is a separate, redundant
# opt-out mechanism outside the request form itself). **CAPTCHA solution
# required** for reCAPTCHA regardless.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.lead411.com/your-privacy-choices/"

REQUEST_TYPES = ["Access My Personal Information", "Opt-out of the Sale of My Personal Information"]
DELETE_REQUEST_TYPE = "Delete My Personal Information"


async def submit_request(tab, request_type, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    accept_btn = await tab.find(id="CybotCookiebotDialogBodyButtonAccept", raise_exc=False)
    if accept_btn:
        await accept_btn.click()
        await asyncio.sleep(1)

    request_select = await tab.find(id="select_option_for_profile", raise_exc=False)
    if request_select:
        await request_select.execute_script(
            "for (var i=0;i<this.options.length;i++){"
            f"  if(this.options[i].text==={request_type!r}){{ this.selectedIndex=i; }}"
            "}"
            "this.dispatchEvent(new Event('change', {bubbles:true}));"
        )

    country_select = await tab.find(id="countries", raise_exc=False)
    if country_select:
        await country_select.execute_script(
            "for (var i=0;i<this.options.length;i++){"
            "  if(this.options[i].text==='United States'){ this.selectedIndex=i; }"
            "}"
            "this.dispatchEvent(new Event('change', {bubbles:true}));"
        )
        await asyncio.sleep(1)

    state_select = await tab.find(id="us-states", raise_exc=False)
    if state_select:
        await state_select.execute_script(
            "for (var i=0;i<this.options.length;i++){"
            f"  if(this.options[i].text==={SuperScraper.STATE!r}){{ this.selectedIndex=i; }}"
            "}"
            "this.dispatchEvent(new Event('change', {bubbles:true}));"
        )

    email_field = await tab.find(id="employee_email", raise_exc=False)
    if email_field:
        await email_field.type_text(SuperScraper.EMAIL)

    agree_checkbox = await tab.find(id="i_agree", raise_exc=False)
    if agree_checkbox:
        # native .click() raises ElementNotVisible — the real <input> is
        # visually replaced by custom checkbox styling; set + dispatch via
        # JS instead
        await agree_checkbox.execute_script(
            "this.checked=true;"
            "this.dispatchEvent(new Event('click', {bubbles:true}));"
            "this.dispatchEvent(new Event('change', {bubbles:true}));"
        )

    label = request_type.lower().replace(" ", "_").replace("-", "_")

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/lead411_dry_run_{label}.png")
    print(
        f"\n'{request_type}' request filled but NOT sent — solve the reCAPTCHA and click "
        "'Get Code' yourself, then enter the verification code you receive. This emails a "
        "real code regardless of DRY_RUN, so it is never done automatically."
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    request_types = list(REQUEST_TYPES)
    if SuperScraper.REMOVE_INFORMATION:
        request_types.append(DELETE_REQUEST_TYPE)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for request_type in request_types:
            await submit_request(tab, request_type, super_scraper)


asyncio.run(main())
