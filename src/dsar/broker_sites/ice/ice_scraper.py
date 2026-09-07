# ice.com (Intercontinental Exchange) — custom OneTrust Angular DSAR portal.
# Subject: "Customer". Country: "United States" → State: "Minnesota" (both autocomplete).
# Line of Service: "Data Services". Request type is SINGLE-SELECT — one submission per right.
# Fields: subjectTypesDSARElement, countryDSARElement, stateDSARElement (appears after country),
#   formField85DSARElement (Line of Service), requestTypesDSARElement,
#   First Name / Last Name via aria-label, emailDSARElement,
#   formField82DSARElement (phone, optional), requestDetailsDSARElement (textarea).
# CAPTCHA: id="captchaCode", BotDetect 6-char alphanumeric, manual entry per submission.
# Always: Info Request, Update Data, Object to Processing, Data Portability, Restrict Processing.
# Gated on REMOVE_INFORMATION: Data Deletion.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = "https://ice-privacy.my.onetrust.com/webform/cca3ac39-00b6-45f4-819b-bec660878b46/124d1692-407b-4384-9036-bef3ece530e3"

ALWAYS_REQUESTS = [
    ("Info Request", "access",
     "I am exercising my right to access and obtain a copy of my personal information held by ICE Data Services."),
    ("Update Data", "correct",
     "I am exercising my right to correct and update my personal information held by ICE Data Services."),
    ("Object to Processing", "object",
     "I am exercising my right to opt-out of and object to the processing of my personal information by ICE Data Services."),
    ("Data Portability", "portability",
     "I am exercising my right to data portability for my personal information held by ICE Data Services."),
    ("Restrict Processing", "restrict",
     "I am exercising my right to restrict the processing of my personal information by ICE Data Services."),
]
DELETE_REQUEST = (
    "Data Deletion", "delete",
    "I am exercising my right to delete my personal information held by ICE Data Services."
)


async def _autocomplete_select(tab, field_id, search, option_text):
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        return False
    await field.click()
    if search:
        await field.type_text(search)
    await asyncio.sleep(2)
    opts = await tab.find(**{"role": "option"}, find_all=True, raise_exc=False) or []
    for o in opts:
        if await o.is_visible():
            t = await o.text
            if t and t.strip() == option_text:
                await o.click()
                await asyncio.sleep(1)
                return True
    for o in opts:
        if await o.is_visible():
            await o.click()
            await asyncio.sleep(1)
            return True
    return False


async def _submit_request(tab, req_type, label, details, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(8)

    await _autocomplete_select(tab, "subjectTypesDSARElement", "", "Customer")
    await _autocomplete_select(tab, "countryDSARElement", "United States", "United States")
    await asyncio.sleep(2)

    await _autocomplete_select(tab, "stateDSARElement", SuperScraper.STATE, SuperScraper.STATE)
    await _autocomplete_select(tab, "formField85DSARElement", "", "Data Services")
    await _autocomplete_select(tab, "requestTypesDSARElement", "", req_type)

    first = await tab.find(**{"aria-label": "First Name"}, raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)
    time.sleep(0.3)

    last = await tab.find(**{"aria-label": "Last Name"}, raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)
    time.sleep(0.3)

    email = await tab.find(id="emailDSARElement", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)
    time.sleep(0.3)

    phone = await tab.find(id="formField82DSARElement", raise_exc=False)
    if phone:
        await phone.type_text(SuperScraper.PHONE_NUMBER)
    time.sleep(0.3)

    details_field = await tab.find(id="requestDetailsDSARElement", raise_exc=False)
    if details_field:
        await details_field.type_text(details)
    time.sleep(0.3)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        captcha_field = await tab.find(id="captchaCode", raise_exc=False)
        if captcha_field:
            await captcha_field.scroll_into_view()
        await asyncio.sleep(1)
        await tab.take_screenshot(f"ice_dry_run_{label}.png")
        print(f"Screenshot saved to ice_dry_run_{label}.png")
        return

    captcha_field = await tab.find(id="captchaCode", raise_exc=False)
    if captcha_field:
        await captcha_field.scroll_into_view()
    print(f"\nForm filled for '{label}'. Enter the 6-char CAPTCHA code, then press Enter.")
    code = input("CAPTCHA code: ").strip()
    if captcha_field:
        await captcha_field.type_text(code)
    time.sleep(0.3)

    submit_btn = await tab.find(text="Submit", raise_exc=False)
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(5)

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{label}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{label}' — verify in browser")


async def main():
    opts = ChromiumOptions()
    super_scraper = SuperScraper()
    opts.binary_location = super_scraper.CHROMIUM_LOCATION
    opts.add_argument("--no-sandbox")

    requests = list(ALWAYS_REQUESTS)
    if SuperScraper.REMOVE_INFORMATION:
        requests.append(DELETE_REQUEST)

    async with Chrome(options=opts) as browser:
        tab = await browser.start()
        for req_type, label, details in requests:
            await _submit_request(tab, req_type, label, details, super_scraper)


asyncio.run(main())
