# precisely.com — two separate OneTrust webforms sharing the same base
# portal id (d88b298e-...) but different second segments: one for
# Precisely itself, one for its PlaceIQ subsidiary. Both are cascading
# single-page forms (later fields only render in the DOM once earlier
# ones are answered — inspect a fresh load before assuming a field is
# missing) with a role="option" toggle-button "Select Privacy Right"
# group that's single-select despite offering many options — one
# submission per right.
#
# Precisely form: "I am submitting this request as" (Myself/Authorized
# Agent, role="option" toggle) -> Country (autocomplete combobox) -> State
# (autocomplete combobox, formField97DSARElement) -> "Your relationship
# with Precisely" (role="option" toggle: Website Visitor/Customer/
# Employee/etc — "Website Visitor" used, closest generic fit) -> "Select
# which Privacy Right you seek to exercise" (role="option" toggle) ->
# Full Name/Email/Request Detail/Under-which-law (all revealed only after
# the right is picked).
#
# PlaceIQ form: US State (autocomplete combobox, formField103DSARElement)
# -> "I am submitting this request as" (subjectTypesDSARElement — an
# autocomplete COMBOBOX here, not a toggle group like the Precisely form's
# equivalent field, despite the same wording) -> "Your relationship with
# Precisely" (Partner/Customer/Consumer, role="option" — "Consumer" used)
# -> "Request Type" (role="option", single-select) -> Full Name/Email.
# Selecting the Opt-out request type specifically reveals one more
# required field, a MAID (formField83DSARElement) — PlaceIQ's own copy on
# that step notes it treats any Opt-Out request as a deletion request and
# adds the MAID to its suppression list. That field validates against a
# strict UUID-shaped format (XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX); this
# repo's .env ADVERTISING_ID placeholder ("0000-0000-0000-0000") doesn't
# match it and the field shows a validation error in the screenshot — a
# persona-data limitation, not a scraper bug. A real run needs an
# ADVERTISING_ID in genuine UUID form.
#
# Both forms: reCAPTCHA v2 — **CAPTCHA solution required**. Exercises
# Access ("Right to Know - Categories") and Opt-Out unconditionally;
# Delete gated on REMOVE_INFORMATION, on both forms.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

PRECISELY_URL = "https://privacyportal-eu.onetrust.com/webform/d88b298e-1f7e-420f-949c-fedc475c1e77/draft/9c253316-9abf-49fb-a3e1-a4e214c4cf41"
PLACEIQ_URL = "https://privacyportal-eu.onetrust.com/webform/d88b298e-1f7e-420f-949c-fedc475c1e77/83126462-6c9f-4d90-9077-f029b129a2a6"

PRECISELY_RIGHTS = ["Right to Know - Categories", "Right to Opt Out of the Sale of Personal Information"]
PRECISELY_DELETE_RIGHT = "Right to Delete"

PLACEIQ_RIGHTS = ["Right to Know - Categories", "Opt-out of the Sale/Sharing of Personal Information"]
PLACEIQ_DELETE_RIGHT = "Delete Personal Information"


async def _autocomplete_select(tab, field_id, text, super_scraper, description):
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        print(f"{super_scraper.OOPS} {description} field not found")
        return False
    await field.click()
    await asyncio.sleep(0.3)
    await tab.keyboard.type_text(text)
    await asyncio.sleep(1.2)
    option = await tab.find(xpath=f"//*[@role='option' and normalize-space()='{text}']", raise_exc=False)
    if option:
        await option.click()
        await asyncio.sleep(0.7)
        return True
    print(f"{super_scraper.OOPS} {description} option '{text}' not found")
    return False


async def _toggle_select(tab, option_text, super_scraper, description):
    option = await tab.find(xpath=f"//*[@role='option' and normalize-space()='{option_text}']", raise_exc=False)
    if option:
        await option.click()
        await asyncio.sleep(0.7)
        return True
    print(f"{super_scraper.OOPS} {description} option '{option_text}' not found")
    return False


async def submit_precisely(tab, right, super_scraper):
    await tab.go_to(PRECISELY_URL)
    await asyncio.sleep(5)

    await _toggle_select(tab, "Myself", super_scraper, "submitter type")
    submit_btn = await tab.find(text="Submit", raise_exc=False)
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(2)

    await _autocomplete_select(tab, "countryDSARElement", "United States", super_scraper, "country")
    await _autocomplete_select(tab, "formField97DSARElement", SuperScraper.STATE, super_scraper, "state")
    await _toggle_select(tab, "Website Visitor", super_scraper, "relationship")
    await _toggle_select(tab, right, super_scraper, "privacy right")

    name_field = await tab.find(id="firstNameDSARElement", raise_exc=False)
    if name_field:
        await name_field.type_text(f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    email_field = await tab.find(id="emailDSARElement", raise_exc=False)
    if email_field:
        await email_field.type_text(SuperScraper.EMAIL)

    label = "".join(c if c.isalnum() else "_" for c in right.lower())[:40].strip("_")
    await asyncio.sleep(1)
    await tab.take_screenshot(path=f"resources/screenshots/precisely_dry_run_{label}.png")
    print(f"Screenshot saved to resources/screenshots/precisely_dry_run_{label}.png")
    print(f"\n[Precisely] '{right}' request filled but NOT submitted — reCAPTCHA v2 requires a manual solve.")


async def submit_placeiq(tab, right, super_scraper):
    await tab.go_to(PLACEIQ_URL)
    await asyncio.sleep(5)

    await _autocomplete_select(tab, "formField103DSARElement", SuperScraper.STATE, super_scraper, "state")
    await _autocomplete_select(tab, "subjectTypesDSARElement", "Myself", super_scraper, "submitter type")
    await _toggle_select(tab, "Consumer", super_scraper, "relationship")
    await _toggle_select(tab, right, super_scraper, "request type")

    name_field = await tab.find(id="firstNameDSARElement", raise_exc=False)
    if name_field:
        await name_field.type_text(f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    email_field = await tab.find(id="emailDSARElement", raise_exc=False)
    if email_field:
        await email_field.type_text(SuperScraper.EMAIL)

    # Selecting the Opt-out request type reveals an additional required
    # MAID field (formField83DSARElement) not present for other rights —
    # PlaceIQ's own copy on that step notes it treats any Opt-Out request
    # as a deletion request and adds the MAID to its suppression list.
    maid_field = await tab.find(id="formField83DSARElement", raise_exc=False)
    if maid_field and SuperScraper.ADVERTISING_ID:
        await maid_field.type_text(SuperScraper.ADVERTISING_ID)

    label = "".join(c if c.isalnum() else "_" for c in right.lower())[:40].strip("_")
    await asyncio.sleep(1)
    await tab.take_screenshot(path=f"resources/screenshots/placeiq_dry_run_{label}.png")
    print(f"Screenshot saved to resources/screenshots/placeiq_dry_run_{label}.png")
    print(f"\n[PlaceIQ] '{right}' request filled but NOT submitted — reCAPTCHA v2 requires a manual solve.")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    precisely_rights = list(PRECISELY_RIGHTS)
    placeiq_rights = list(PLACEIQ_RIGHTS)
    if SuperScraper.REMOVE_INFORMATION:
        precisely_rights.append(PRECISELY_DELETE_RIGHT)
        placeiq_rights.append(PLACEIQ_DELETE_RIGHT)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in precisely_rights:
            await submit_precisely(tab, right, super_scraper)
        for right in placeiq_rights:
            await submit_placeiq(tab, right, super_scraper)


asyncio.run(main())
