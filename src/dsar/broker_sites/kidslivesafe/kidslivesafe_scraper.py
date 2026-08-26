# kidslivesafe.com — help-center/privacy-requests. A single form with a
# "Request Type" select (Do Not Sell My Info / Delete My Info / Request a
# Copy) — one submission per type. First/Last/City/State/ZIP/Age are
# always required; the Last Name field's real `name`/`id` is a random hex
# string ("ac5ccdde8ce2a780d" at the time this was written, may change) —
# an anti-bot obfuscation technique, not a stable identifier, so it's
# targeted positionally (the 3rd plain `input[type=text]` on the page —
# order is customerId, firstName, Last Name, city, zip) rather than by
# name/id. Email only appears (conditionally
# revealed by JS) when "Request a Copy" is selected, since that's the only
# request type that delivers something back to you. Age is a numeric
# select (18-105) — DATE_OF_BIRTH is converted to an age and clamped into
# that range. A Cloudflare Turnstile checkbox gates the "Continue" button —
# **CAPTCHA solution required**; the form is filled completely regardless
# and left at the CAPTCHA per this repo's standard policy. Exercises Do Not
# Sell and Request a Copy unconditionally; Delete gated on
# REMOVE_INFORMATION.
import asyncio
from datetime import datetime

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.kidslivesafe.com/help-center/privacy-requests"

REQUEST_TYPES = ["Do Not Sell My Info", "Request a Copy"]
DELETE_REQUEST_TYPE = "Delete My Info"


def _age_from_dob(dob_str):
    try:
        day, month, year = dob_str.split("/")
        age = datetime.now().year - int(year)
    except (ValueError, AttributeError):
        return "30"
    return str(min(max(age, 18), 105))


async def submit_request(tab, request_type, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    request_select = await tab.find(id="requestType", raise_exc=False)
    if request_select:
        await request_select.execute_script(
            "for (var i=0;i<this.options.length;i++){"
            f"  if(this.options[i].text==={request_type!r}){{ this.selectedIndex=i; }}"
            "}"
            "this.dispatchEvent(new Event('change', {bubbles:true}));"
        )
        await asyncio.sleep(0.5)

    first_field = await tab.find(id="firstName", raise_exc=False)
    if first_field:
        await first_field.type_text(SuperScraper.FIRST_NAME)

    # text-input order on this form: customerId(1), firstName(2), Last Name
    # -- the obfuscated-name field(3), city(4), zip(5)
    last_field = await tab.find(
        xpath="(//input[@type='text'])[3]", raise_exc=False
    )
    if last_field:
        await last_field.type_text(SuperScraper.LAST_NAME)

    city_field = await tab.find(id="city", raise_exc=False)
    if city_field:
        await city_field.type_text(SuperScraper.CITY)

    state_select = await tab.find(id="states", raise_exc=False)
    if state_select:
        await state_select.execute_script(
            "for (var i=0;i<this.options.length;i++){"
            f"  if(this.options[i].text==={SuperScraper.STATE!r}){{ this.selectedIndex=i; }}"
            "}"
            "this.dispatchEvent(new Event('change', {bubbles:true}));"
        )

    zip_field = await tab.find(id="zip", raise_exc=False)
    if zip_field:
        await zip_field.type_text(SuperScraper.ZIP_CODE)

    age_select = await tab.find(id="age", raise_exc=False)
    if age_select:
        age_value = _age_from_dob(SuperScraper.DATE_OF_BIRTH)
        await age_select.execute_script(
            "for (var i=0;i<this.options.length;i++){"
            f"  if(this.options[i].text==={age_value!r}){{ this.selectedIndex=i; }}"
            "}"
            "this.dispatchEvent(new Event('change', {bubbles:true}));"
        )

    if request_type == "Request a Copy":
        email_field = await tab.find(id="email", raise_exc=False)
        if email_field:
            await email_field.type_text(SuperScraper.EMAIL)

    label = request_type.lower().replace(" ", "_")

    await asyncio.sleep(1)
    await tab.take_screenshot(path=f"resources/screenshots/kidslivesafe_dry_run_{label}.png")
    print(f"Screenshot saved to resources/screenshots/kidslivesafe_dry_run_{label}.png")
    print(
        f"\n'{request_type}' request filled but NOT submitted — a Cloudflare Turnstile "
        "checkbox gates the 'Continue' button and requires a manual solve."
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
