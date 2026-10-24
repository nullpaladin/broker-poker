# samba.tv — exercises Do Not Sell, Object to Processing, Access, and Delete
# (each gated by SuperScraper.rights_to_exercise(RIGHT_MAP)). "File a Complaint or Appeal" and "Other" skipped.
# OneTrust CDN Angular form. "Do you have a Samba Enabled Smart TV?" answered
# No (most users don't own a Samba-branded TV). Country is an autocomplete
# combobox (click → keyboard.type_text → find(text=)). Phone country code
# (vt-input-7) set to "+1". captchaCode text input requires manual entry in
# live mode. No state field. Submits once per right type.
#
# Page elements:
#   aria-label "Myself " (or "Myself")    "I am" button
#   aria-label "Access My Information" / "Do Not Sell My Information" /
#              "Object to Processing My Information" / "Delete My Information"   request-type buttons
#   aria-label "No"                       "Do you have a Samba Enabled Smart TV?"
#   #firstNameDSARElement / #lastNameDSARElement / #emailDSARElement
#   #countryDSARElement                   Country autocomplete -> "United States"
#   #vt-input-7                           phone country code (type "1")
#   #phoneNumberDSARElement               Phone
#   #captchaCode                          image CAPTCHA (manual entry)
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal-cdn.onetrust.com/dsarwebform/87c5ee85-893d-4972-ba26-2e82b743d041/d84d9664-facb-4de3-85fd-a2e339b73dbf.html"

# Right -> [(aria-label, screenshot label)]
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("Access My Information", "access")],
    Right.RIGHT_TO_OPT_OUT: [
        ("Do Not Sell My Information", "optout"),
        ("Object to Processing My Information", "object"),
    ],
    Right.RIGHT_TO_DELETE: [("Delete My Information", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (Recorded request types are aria-labels; the visible text may differ, so they are not copied in.)

FIELD_XPATHS = {
    "First name": "//*[@id='firstNameDSARElement']",
    "Last name": "//*[@id='lastNameDSARElement']",
    "Email": "//*[@id='emailDSARElement']",
    "Country": "//*[@id='countryDSARElement']",
    "Phone": "//*[@id='phoneNumberDSARElement']",
}


async def submit_request(tab, aria_label, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    myself_btn = await tab.find(**{"aria-label": "Myself "}, raise_exc=False)
    if not myself_btn:
        myself_btn = await tab.find(**{"aria-label": "Myself"}, raise_exc=False)
    if myself_btn:
        await myself_btn.click_using_js()
    await asyncio.sleep(1)

    req_btn = await tab.find(**{"aria-label": aria_label}, raise_exc=False)
    if not req_btn:
        print(f"{super_scraper.OOPS} Request button '{aria_label}' not found")
        return
    await req_btn.click_using_js()
    await asyncio.sleep(1)

    # "Do you have a Samba Enabled Smart TV?" — required; click No
    no_btn = await tab.find(**{"aria-label": "No"}, raise_exc=False)
    if no_btn:
        await no_btn.click_using_js()
    await asyncio.sleep(0.5)

    first = await tab.find(id="firstNameDSARElement", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)

    last = await tab.find(id="lastNameDSARElement", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)

    email = await tab.find(id="emailDSARElement", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    # Country autocomplete: click → keyboard type → find by text
    country_field = await tab.find(id="countryDSARElement", raise_exc=False)
    if country_field:
        await country_field.click()
        await tab.keyboard.type_text("United States")
        await asyncio.sleep(2)
        country_opt = await tab.find(text="United States", raise_exc=False)
        if country_opt:
            await country_opt.click()
    await asyncio.sleep(1)

    # Phone country code (vt-input-7) — type "1" for US; no dropdown selection
    # ("+1" text is too ambiguous to safely find the correct dropdown option)
    phone_cc = await tab.find(id="vt-input-7", raise_exc=False)
    if phone_cc:
        await phone_cc.click()
        await tab.keyboard.type_text("1")
    await asyncio.sleep(0.5)

    phone = await tab.find(id="phoneNumberDSARElement", raise_exc=False)
    if phone:
        await phone.type_text(SuperScraper.PHONE_NUMBER)

    time.sleep(0.5)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{aria_label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        captcha_field = await tab.find(id="captchaCode", raise_exc=False)
        if captcha_field:
            await captcha_field.scroll_into_view()
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
        return

    print(f"\nForm filled for '{aria_label}'.")
    print("Enter the CAPTCHA code shown in the browser into the captchaCode field,")
    print("then click Submit. Press Enter after the confirmation page appears...")
    input()

    print(f"Submitted '{aria_label}' for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    requests = [entry for right in rights for entry in RIGHT_MAP[right]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for aria_label, label in requests:
            await submit_request(tab, aria_label, label, super_scraper)


asyncio.run(main())
