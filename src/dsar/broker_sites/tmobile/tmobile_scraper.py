# t-mobile.com — custom OneTrust Angular "T-Privacy Center" portal. Heavily
# cascading form — Access and Delete diverge in which fields ultimately
# appear, so don't trust a single exploration pass; re-screenshot after
# selecting Type of request AND after selecting the fields it reveals.
#
# "Requestor" (formField79DSARElement) is a vt-autocomplete combobox;
# clicking it (no typing needed) immediately shows three options — "I am
# requesting my own personal data" is used. "Type of request"
# (requestTypesDSARElement) is a role=listbox toggle group — the page's own
# copy says "If you want to access and delete your personal data, you'll
# need to submit two separate requests," confirming single-select — one
# submission per right: Access personal data (access), Delete personal data
# (delete); which run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP). Correct personal data skipped
# (no concrete inaccuracy to describe).
#
# Selecting a Type of request reveals fields common to BOTH rights:
# "Relationship with T-Mobile" (subjectTypesDSARElement, toggle group —
# "Current customer" used), "US States & Territories"
# (formField112DSARElement, toggle group — "Continental US, AK, HI, DC"
# used for all US states), "State of residence" (stateDSARElement,
# vt-autocomplete — only rendered AFTER Relationship is answered), Phone
# Number, Email. The two rights then DIVERGE: Access additionally requires
# "Delivery method" (formField77DSARElement, single-option toggle "Secure
# online portal"); Delete additionally requires First Name, Last Name,
# Street address (formField84DSARElement), City, Zip code — none of which
# Access asks for at all. reCAPTCHA v2 — **CAPTCHA solution required**.
#
# Page elements:
#   formField79DSARElement    "Requestor" -> "I am requesting my own personal data"
#   requestTypesDSARElement   "Type of request" (see RIGHT_MAP)
#   subjectTypesDSARElement   "Relationship with T-Mobile" -> "Current customer"
#   formField112DSARElement   "US States & Territories" -> "Continental US, AK, HI, DC"
#   stateDSARElement          "State of residence"
#   phoneNumberDSARElement    Phone Number
#   emailDSARElement          Email
#   formField77DSARElement    "Delivery method" (Access only) -> "Secure online portal"
#   firstNameDSARElement / lastNameDSARElement / formField84DSARElement (Street address) /
#   cityDSARElement / zipDSARElement   First name, Last name, Street address, City, Zip code (Delete only)
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://privacyportal-t-mobile.my.onetrust.com/webform/d4a925f0-4ebf-40ba-817b-bccc309e602f/7831d667-1ebc-4b1e-a941-e545cb0d0523"

# Right -> "Type of request" option.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Access personal data",
    Right.RIGHT_TO_DELETE: "Delete personal data",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)
DELETE_REQUEST_TYPE = RIGHT_MAP[Right.RIGHT_TO_DELETE]


async def _select_option(tab, option_text, super_scraper, description):
    option = await tab.find(xpath=f"//*[@role='option' and normalize-space()='{option_text}']", raise_exc=False)
    if option:
        await option.click()
        await asyncio.sleep(0.5)
    else:
        print(f"{super_scraper.OOPS} {description} option '{option_text}' not found")


async def submit_request(tab, request_type, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    requestor_field = await tab.find(id="formField79DSARElement", raise_exc=False)
    if requestor_field:
        await requestor_field.click()
        await asyncio.sleep(0.7)
        await _select_option(tab, "I am requesting my own personal data", super_scraper, "Requestor")
    else:
        print(f"{super_scraper.OOPS} Requestor field not found")

    await _select_option(tab, request_type, super_scraper, "Type of request")
    await _select_option(tab, "Current customer", super_scraper, "Relationship with T-Mobile")
    await _select_option(tab, "Continental US, AK, HI, DC", super_scraper, "US States & Territories")

    state_field = await tab.find(id="stateDSARElement", raise_exc=False)
    if state_field:
        await state_field.click()
        await asyncio.sleep(0.3)
        await tab.keyboard.type_text(SuperScraper.STATE)
        await asyncio.sleep(1.2)
        option = await tab.find(
            xpath=f"//*[@role='option' and normalize-space()='{SuperScraper.STATE}']", raise_exc=False
        )
        if option:
            await option.click()
            await asyncio.sleep(0.7)
        else:
            print(f"{super_scraper.OOPS} State of residence option '{SuperScraper.STATE}' not found")
    else:
        print(f"{super_scraper.OOPS} State of residence field not found")

    phone_field = await tab.find(id="phoneNumberDSARElement", raise_exc=False)
    if phone_field and SuperScraper.PHONE_NUMBER:
        await phone_field.type_text(SuperScraper.PHONE_NUMBER)

    email_field = await tab.find(id="emailDSARElement", raise_exc=False)
    if email_field:
        await email_field.type_text(SuperScraper.EMAIL)
    else:
        print(f"{super_scraper.OOPS} Email field not found")

    if request_type == DELETE_REQUEST_TYPE:
        fields = {
            "firstNameDSARElement": SuperScraper.FIRST_NAME,
            "lastNameDSARElement": SuperScraper.LAST_NAME,
            "formField84DSARElement": SuperScraper.ADDRESS,
            "cityDSARElement": SuperScraper.CITY,
            "zipDSARElement": SuperScraper.ZIP_CODE,
        }
        for field_id, value in fields.items():
            if not value:
                continue
            field = await tab.find(id=field_id, raise_exc=False)
            if field:
                await field.type_text(value)
            else:
                print(f"{super_scraper.OOPS} field '{field_id}' not found")
    else:
        await _select_option(tab, "Secure online portal", super_scraper, "Delivery method")

    label = "".join(c if c.isalnum() else "_" for c in request_type.lower())[:40].strip("_")
    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{label}")
    print(
        f"\n'{request_type}' request filled but NOT submitted — a reCAPTCHA v2 checkbox "
        "requires a manual solve before submitting."
    )


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    request_types = [RIGHT_MAP[right] for right in rights]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for request_type in request_types:
            await submit_request(tab, request_type, super_scraper)


asyncio.run(main())
