# madisonlogic.com — Custom OneTrust portal (madisonlogic-privacy.my.onetrust.com).
# Despite "(s)" labels, BOTH the main request type buttons AND the opt-out
# sub-option buttons are SINGLE-SELECT per submission — one form fill per right.
# Country must be filled first to reveal State, subject type, and request type.
# Subject type "Data Subject". requestDetailsDSARElement is always required.
# "Opt out" reveals two sub-options: "Partner Services Marketing" and
# "Personalized Content" — each requires a separate submission.
# If "Data Deletion" is selected, a Yes/No confirmation appears; click "Yes".
# Phone country code vt-input-7 (optional). Image CAPTCHA (captchaCode).
# Rights exercised: Opt out (2 sub-options), Info Request (Access), Correct Data,
# Object to Processing, Data Portability, Restrict Processing,
# Do Not Sell My Information.
# Data Deletion gated on REMOVE_INFORMATION.
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://madisonlogic-privacy.my.onetrust.com/webform/b7449bea-44c6-4823-a2ac-30a8f33047d0/9a375b0c-9030-44ce-bfd3-217fd7a71993"

# (req_aria, label, sub_option_aria_or_None)
ALWAYS_REQUESTS = [
    ("Opt out",                    "optout_marketing",    "Partner Services Marketing"),
    ("Opt out",                    "optout_content",      "Personalized Content"),
    ("Info Request",               "access",              None),
    ("Correct Data",               "correct",             None),
    ("Object to Processing",       "object",              None),
    ("Data Portability",           "portability",         None),
    ("Restrict Processing",        "restrict",            None),
    ("Do Not Sell My Information", "dns",                 None),
]
DELETE_REQUEST = ("Data Deletion", "delete", None)


async def _autocomplete(tab, field_id, text):
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        return
    await field.click()
    await field.type_text(text)
    await asyncio.sleep(2)
    opts = await tab.find(**{"role": "option"}, find_all=True, raise_exc=False) or []
    for opt in opts:
        if await opt.is_visible():
            t = await opt.text
            if t and t.strip() == text:
                await opt.click()
                await asyncio.sleep(1)
                return


async def _submit_request(tab, req_aria, label, sub_option, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(7)

    # Country first (reveals state, subject type, and request type buttons)
    await _autocomplete(tab, "countryDSARElement", "United States")
    await asyncio.sleep(2)

    # State (appears after country)
    await _autocomplete(tab, "stateDSARElement", SuperScraper.STATE)
    await asyncio.sleep(1)

    # Subject type
    data_subject_btn = await tab.find(**{"aria-label": "Data Subject"}, raise_exc=False)
    if data_subject_btn:
        await data_subject_btn.click_using_js()
    else:
        print(f"{super_scraper.OOPS} 'Data Subject' button not found for {label}")
        return
    await asyncio.sleep(0.5)

    # Request type (single-select)
    req_btn = await tab.find(**{"aria-label": req_aria}, raise_exc=False)
    if req_btn:
        await req_btn.click_using_js()
    else:
        print(f"{super_scraper.OOPS} Request button '{req_aria}' not found")
        return
    await asyncio.sleep(0.5)

    # Click sub-option if applicable (single-select sub-listbox)
    if sub_option:
        sub_btn = await tab.find(**{"aria-label": sub_option}, raise_exc=False)
        if sub_btn:
            await sub_btn.click_using_js()
        else:
            print(f"{super_scraper.OOPS} Sub-option '{sub_option}' not found")
        await asyncio.sleep(0.3)

    # Deletion confirmation dialog (appears when Data Deletion is selected)
    if label == "delete":
        yes_btn = await tab.find(**{"aria-label": "Yes"}, raise_exc=False)
        if yes_btn:
            await yes_btn.click_using_js()
        await asyncio.sleep(0.5)

    # Personal info
    first = await tab.find(id="firstNameDSARElement", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)

    last = await tab.find(id="lastNameDSARElement", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)

    email = await tab.find(id="emailDSARElement", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    # Request Details (always required)
    request_details = await tab.find(id="requestDetailsDSARElement", raise_exc=False)
    if request_details:
        await request_details.type_text(
            f"I am exercising my privacy rights under applicable law ({label})."
        )

    # Phone country code (optional)
    phone_cc = await tab.find(id="vt-input-7", raise_exc=False)
    if phone_cc:
        await phone_cc.click()
        await phone_cc.type_text("1")
    await asyncio.sleep(0.5)

    phone = await tab.find(id="phoneNumberDSARElement", raise_exc=False)
    if phone:
        await phone.type_text(SuperScraper.PHONE_NUMBER)

    if SuperScraper.DRY_RUN:
        sub_desc = f" ({sub_option})" if sub_option else ""
        print(
            f"DRY RUN: would submit '{label}'{sub_desc} for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        captcha_field = await tab.find(id="captchaCode", raise_exc=False)
        if captcha_field:
            await captcha_field.scroll_into_view()
        await asyncio.sleep(1)
        await tab.take_screenshot(f"resources/screenshots/madisonlogic_dry_run_{label}.png")
        print(f"Screenshot saved to resources/screenshots/madisonlogic_dry_run_{label}.png")
        return

    sub_desc = f" ({sub_option})" if sub_option else ""
    print(
        f"\nForm filled for '{label}'{sub_desc}. "
        f"Enter the CAPTCHA code, then click Submit. "
        f"Press Enter after confirmation..."
    )
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{label}'{sub_desc} for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{label}'{sub_desc} — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    requests = list(ALWAYS_REQUESTS)
    if SuperScraper.REMOVE_INFORMATION:
        requests.append(DELETE_REQUEST)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for req_aria, label, sub_option in requests:
            await _submit_request(tab, req_aria, label, sub_option, super_scraper)


asyncio.run(main())
