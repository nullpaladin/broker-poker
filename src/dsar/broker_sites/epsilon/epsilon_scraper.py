# epsilon.com — exercises Do Not Sell, Do Not Share, Access, Delete,
# Opt-Out of Profiling, and Opt-Out of Sensitive Data (the form also offers Correct,
# which is not automatable and not in RIGHT_MAP).
# Custom React form at legal.epsilon.com/dsr. Country select reveals
# request-type radios and personal info fields. Radio inputs are opacity:0
# behind custom spans — click via parent label. reCAPTCHA v2 invisible
# requires manual solve before submit. Submits once per request type.
#
# Page elements:
#   <option value="US">                       Country select -> United States
#   #onetrust-accept-btn-handler              cookie banner accept button
#   <input value=...>                         request-type radios (values in RIGHT_MAP; click parent label)
#   select[name=user] / option consumer       "Consumer" user-type select
#   input[name=first] / [name=last] / [name=email]   First / Last name / Email
#   input[name=address] / [name=city] / [name=zip]   Address / City / Zip
#   select[name=state]                        State select (abbreviation values)
#   "Submit request" button
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://legal.epsilon.com/dsr"

# (radio value, screenshot label)
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("access", "access")],
    Right.RIGHT_TO_OPT_OUT: [
        ("sales", "sell"),
        ("share", "share"),
        ("profile", "profile"),
        ("sensitive", "sensitive"),
    ],
    Right.RIGHT_TO_DELETE: [("delete", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
RIGHTS_OPTIONS_CSS = "label:has(input[type='radio'])"  # request-type radios, revealed once a country is chosen

FIELD_XPATHS = {
    "First name": "//*[@name='first']",
    "Last name": "//*[@name='last']",
    "Email": "//*[@name='email']",
    "Address": "//*[@name='address']",
    "City": "//*[@name='city']",
    "Zip": "//*[@name='zip']",
    "State": "//select[@name='state']",
}


async def submit_request(tab, right, radio_value, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    # Select United States
    us_option = await tab.find(tag_name="option", value="US", raise_exc=False)
    if not us_option:
        print(f"{super_scraper.OOPS} Country option US not found")
        return
    await us_option.click()
    await asyncio.sleep(3)

    # Dismiss cookie banner so it doesn't intercept field clicks
    accept_btn = await tab.find(id="onetrust-accept-btn-handler", raise_exc=False)
    if accept_btn:
        await accept_btn.click()
        await asyncio.sleep(1)

    if SuperScraper.HEALTH_CHECK:
        offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
        SuperScraper.audit_rights(offered, PAGE_RIGHTS)

    # Select request type by clicking its label (radio is opacity:0)
    radio = await tab.find(tag_name="input", value=radio_value, raise_exc=False)
    if not radio:
        print(f"{super_scraper.OOPS} Radio '{radio_value}' not found")
        return
    label_el = await radio.get_parent_element()
    await label_el.click()
    await asyncio.sleep(3)  # wait for React to render personal info fields

    # Select "Consumer" in the user select — scope to that select to avoid
    # matching same-valued options in the country select.
    user_select = await tab.find(tag_name="select", name="user", raise_exc=False)
    if user_select:
        consumer_opt = await user_select.find(tag_name="option", value="consumer", raise_exc=False)
        if consumer_opt:
            await consumer_opt.click()
    time.sleep(0.5)

    # Fill personal info text fields
    first = await tab.find(tag_name="input", name="first", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)

    last = await tab.find(tag_name="input", name="last", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)

    email = await tab.find(tag_name="input", name="email", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    address = await tab.find(tag_name="input", name="address", raise_exc=False)
    if address:
        await address.type_text(SuperScraper.ADDRESS)

    city = await tab.find(tag_name="input", name="city", raise_exc=False)
    if city:
        await city.type_text(SuperScraper.CITY)

    zip_field = await tab.find(tag_name="input", name="zip", raise_exc=False)
    if zip_field:
        await zip_field.type_text(SuperScraper.ZIP_CODE)

    # State select — scope to state select to avoid country select collisions
    state_abbrev = SuperScraper.STATE_ABBREVIATED
    state_select = await tab.find(tag_name="select", name="state", raise_exc=False)
    if state_select:
        state_opt = await state_select.find(tag_name="option", value=state_abbrev, raise_exc=False)
        if state_opt:
            await state_opt.click()
        else:
            print(f"{super_scraper.OOPS} State '{state_abbrev}' not in dropdown")

    time.sleep(0.5)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right.name}' ({radio_value}) for {SuperScraper.EMAIL}"
        )
        submit_btn = await tab.find(tag_name="button", text="Submit request", raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await asyncio.sleep(2)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}_{label}")
        return

    print(f"\nForm filled for '{right.name}' ({radio_value}).")
    print("Solve the reCAPTCHA in the browser, then click Submit.")
    print("Press Enter after the confirmation page appears...")
    input()

    print(f"Submitted '{right.name}' ({radio_value}) for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()
    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            for radio_value, label in RIGHT_MAP[right]:
                await submit_request(tab, right, radio_value, label, super_scraper)


asyncio.run(main())
