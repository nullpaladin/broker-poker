# ididata.com (IDI Data) — exercises Access, Do Not Sell, Delete (gated).
# Three separate Salesforce Web-to-Case pages, one per right type. Minnesota is supported.
# Fields: name, address, state (full name), zip, phone, email, last4ss (LAST_FOUR_SSN required),
# DOB (month/day/year selects), lived6Months ("Yes"), deliveryChoice ("email").
# hp-prefixed selects (hplived6Months, hpdobmonth, etc.) are honeypots — left empty.
# hplegalAgree is a honeypot checkbox — left unchecked.
# reCAPTCHA v2 requires manual solve before submit.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

# (URL, screenshot label)
REQUESTS = [
    ("https://www.ididata.com/personal-information-request/",    "access"),
    ("https://www.ididata.com/do-not-sell-my-personal-information/", "optout"),
]
DELETE_REQUEST = ("https://www.ididata.com/deletion-request/", "delete")


def _parse_dob():
    """Parse DATE_OF_BIRTH (DD/MM/YYYY) → (day_str, month_str, year_str)."""
    dob = SuperScraper.DATE_OF_BIRTH or "01/01/1990"
    parts = dob.split("/")
    day = str(int(parts[0]))
    month = str(int(parts[1]))
    year = parts[2]
    return day, month, year


async def _select_option(tab, select_id, value):
    sel = await tab.find(tag_name="select", id=select_id, raise_exc=False)
    if sel:
        opt = await sel.find(tag_name="option", value=value, raise_exc=False)
        if opt:
            await opt.click()
        else:
            print(f"Option '{value}' not found in select #{select_id}")
    else:
        print(f"Select #{select_id} not found")


async def submit_request(tab, url, label, super_scraper, dob_day, dob_month, dob_year):
    await tab.go_to(url)
    await asyncio.sleep(6)

    # Dismiss cookie banner if present
    accept = await tab.find(text="Accept All Cookies", raise_exc=False)
    if accept and await accept.is_visible():
        await accept.click()
        await asyncio.sleep(1)

    first = await tab.find(id="firstName", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)

    last = await tab.find(id="lastName", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)

    addr1 = await tab.find(id="addressLine1", raise_exc=False)
    if addr1:
        await addr1.type_text(SuperScraper.ADDRESS)

    if SuperScraper.ADDRESS_LINE_TWO:
        addr2 = await tab.find(id="addressLine2", raise_exc=False)
        if addr2:
            await addr2.type_text(SuperScraper.ADDRESS_LINE_TWO)

    city = await tab.find(id="city", raise_exc=False)
    if city:
        await city.type_text(SuperScraper.CITY)

    # State: native <select> with full state name values
    await _select_option(tab, "State", SuperScraper.STATE.title())

    zip_field = await tab.find(id="zip", raise_exc=False)
    if zip_field:
        await zip_field.type_text(SuperScraper.ZIP_CODE)

    # lived6Months: default "Yes" — confirm it's selected
    await _select_option(tab, "lived6Months", "Yes")

    phone = await tab.find(id="phone", raise_exc=False)
    if phone:
        await phone.type_text(SuperScraper.PHONE_NUMBER)

    email = await tab.find(id="email", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    # SSN last 4 (real field, not hp honeypot)
    ssn = await tab.find(id="last4ss", raise_exc=False)
    if ssn:
        await ssn.type_text(SuperScraper.LAST_FOUR_SSN)

    # DOB selects (real fields; hp-prefixed counterparts are honeypots — leave empty)
    await _select_option(tab, "month", dob_month)
    await _select_option(tab, "day", dob_day)
    await _select_option(tab, "year", dob_year)

    # Delivery preference: email
    await _select_option(tab, "deliveryChoice", "email")

    # hplegalAgree is a honeypot — do NOT check it
    time.sleep(0.5)

    if SuperScraper.DRY_RUN:
        submit_btn = await tab.find(tag_name="button", text="Submit Request", raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await SuperScraper.screenshot(tab, f"resources/screenshots/ididata_dry_run_{label}.png")
        print(
            f"DRY RUN: would submit '{label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        return

    print(f"\nForm filled for '{label}'. Solve the reCAPTCHA v2, then click Submit Request.")
    print("Press Enter after the confirmation page appears...")
    input()
    print(f"Submitted '{label}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    if not SuperScraper.LAST_FOUR_SSN:
        print("LAST_FOUR_SSN is required for ididata.com — set it in .env and retry.")
        return

    dob_day, dob_month, dob_year = _parse_dob()

    requests = list(REQUESTS)
    if SuperScraper.REMOVE_INFORMATION:
        requests.append(DELETE_REQUEST)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for url, label in requests:
            await submit_request(tab, url, label, super_scraper, dob_day, dob_month, dob_year)


asyncio.run(main())
