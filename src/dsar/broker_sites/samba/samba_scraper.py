# samba.tv — exercises Do Not Sell, Object to Processing, Access, and Delete
# (gated on REMOVE_INFORMATION). "File a Complaint or Appeal" and "Other" skipped.
# OneTrust CDN Angular form. "Do you have a Samba Enabled Smart TV?" answered
# No (most users don't own a Samba-branded TV). Country is an autocomplete
# combobox (click → keyboard.type_text → find(text=)). Phone country code
# (vt-input-7) set to "+1". captchaCode text input requires manual entry in
# live mode. No state field. Submits once per right type.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal-cdn.onetrust.com/dsarwebform/87c5ee85-893d-4972-ba26-2e82b743d041/d84d9664-facb-4de3-85fd-a2e339b73dbf.html"

# (aria-label, screenshot label)
REQUESTS = [
    ("Do Not Sell My Information", "optout"),
    ("Object to Processing My Information", "object"),
    ("Access My Information", "access"),
]
DELETE_REQUEST = ("Delete My Information", "delete")


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

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{aria_label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        captcha_field = await tab.find(id="captchaCode", raise_exc=False)
        if captcha_field:
            await captcha_field.scroll_into_view()
        await asyncio.sleep(1)
        await tab.take_screenshot(f"resources/screenshots/samba_dry_run_{label}.png")
        print(f"Screenshot saved to resources/screenshots/samba_dry_run_{label}.png")
        return

    print(f"\nForm filled for '{aria_label}'.")
    print("Enter the CAPTCHA code shown in the browser into the captchaCode field,")
    print("then click Submit. Press Enter after the confirmation page appears...")
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{aria_label}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{aria_label}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    requests = list(REQUESTS)
    if SuperScraper.REMOVE_INFORMATION:
        requests.append(DELETE_REQUEST)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for aria_label, label in requests:
            await submit_request(tab, aria_label, label, super_scraper)


asyncio.run(main())
