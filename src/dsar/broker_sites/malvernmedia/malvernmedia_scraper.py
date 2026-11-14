# malvernmedia.com — PrivacyPillar Angular DSAR portal.
# Subject type: radio name="subjecttype", ID="Other US State Resident".
# Request type: radio name="requesttype" — single-select, one submission per right.
# Fields: email (type=email), first_name, last_name, country (typeahead name=country),
#   address, city, state (typeahead name=state), zip.
# Visible text input order: [0]=agency_email(skip), [1]=first, [2]=last,
#   [3]=country(named), [4]=address, [5]=city, [6]=state(named), [7]=zip.
# CAPTCHA: name="captchacode", 6-character alphanumeric image — manual entry in live mode.
# Rights offered: Right to Know, Right to Correct (not automatable, not mapped), Right to
# Opt-Out (Sale/Sharing), Right to Opt-Out (Cross-Behavioral Sale/Sharing), Right to Limit
# Sensitive PI, Right to Delete. Which run is decided only by rights_to_exercise(RIGHT_MAP).
#
# Page elements:
#   input[name=subjecttype]   Subject type radios (label "Other US State Resident" is clicked)
#   input[name=requesttype]   Request type radios (labels listed in RIGHT_MAP)
#   input[type=email]         Email
#   visible text inputs       [1]=First name, [2]=Last name, [4]=Address, [5]=City, [7]=ZIP
#                             ([0] agency email skipped; [3]/[6] are the country/state typeaheads)
#   input[name=country] / input[name=state]   Country / State typeaheads
#   input[name=captchacode]   6-character image CAPTCHA
#   button[type=submit]       Submit
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = (
    "https://privacyportal.privacypillar.com/dsar/form"
    "?formid=6e6ff4b8-2296-4589-ae7f-563fa743ec2d"
    "&orgid=369c8ff9-8ffb-4308-8362-f01691e77db8"
    "&propid=64c8904f-8bac-4dd9-8e6c-d052be1918a2"
    "&status=publish"
)

# Right -> (request-type radio label text, short label for screenshots), or a list of them.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ("Right to Know", "know"),
    Right.RIGHT_TO_OPT_OUT: [
        ("Right to Opt-Out of the Sale or Sharing of Personal Information", "optout_sale"),
        ("Right to Opt-Out of Cross-Behavioral Sale or Sharing", "optout_crossbehavioral"),
        ("Right to Limit Use and Disclosure of Sensitive Personal Information", "limit_sensitive"),
    ],
    Right.RIGHT_TO_DELETE: ("Right to Delete", "delete"),
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every option of the request-type radio, as displayed -> the Right it maps to (None = not automated).
PAGE_RIGHTS = {
    "Right to Know": Right.RIGHT_TO_ACCESS,
    "Right to Correct": None,
    "Right to Opt-Out of the Sale or Sharing of Personal Information": Right.RIGHT_TO_OPT_OUT,
    "Right to Opt-Out of Cross-Behavioral Sale or Sharing": Right.RIGHT_TO_OPT_OUT,
    "Right to Limit Use and Disclosure of Sensitive Personal Information": Right.RIGHT_TO_OPT_OUT,
    "Right to Delete": Right.RIGHT_TO_DELETE,
}
RIGHTS_OPTIONS_CSS = "label:has(input[name='requesttype'])"

FIELD_XPATHS = {
    "Email": "//input[@type='email']",
    "Country": "//*[@name='country']",
    "State": "//*[@name='state']",
}


async def _typeahead(tab, name_attr, search_text):
    field = await tab.find(name=name_attr, raise_exc=False)
    if not field:
        return
    await field.click()
    await field.type_text(search_text)
    await asyncio.sleep(2)
    opt = await tab.find(text=search_text, raise_exc=False)
    if opt and await opt.is_visible():
        await opt.click()
    await asyncio.sleep(1)


async def _submit_request(tab, right_label_text, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(7)

    # Click label elements — the `for` attr matches the radio id, triggering selection
    subject_lbl = await tab.find(text="Other US State Resident", raise_exc=False)
    if subject_lbl:
        await subject_lbl.click()
    else:
        print(f"{super_scraper.OOPS} Subject type label not found for {label}")
        return
    await asyncio.sleep(0.5)

    if SuperScraper.HEALTH_CHECK:
        offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
        SuperScraper.audit_rights(offered, PAGE_RIGHTS)

    req_lbl = await tab.find(text=right_label_text, raise_exc=False)
    if req_lbl:
        await req_lbl.click()
    else:
        print(f"{super_scraper.OOPS} Request type label '{right_label_text}' not found for {label}")
        return
    await asyncio.sleep(0.5)

    email_field = await tab.find(tag_name="input", type="email", raise_exc=False)
    if email_field:
        await email_field.type_text(SuperScraper.EMAIL)
    await asyncio.sleep(0.3)

    all_text = await tab.find(tag_name="input", type="text", find_all=True, raise_exc=False) or []
    visible = [f for f in all_text if await f.is_visible()]
    fill_plan = {
        1: SuperScraper.FIRST_NAME,
        2: SuperScraper.LAST_NAME,
        4: SuperScraper.ADDRESS,
        5: SuperScraper.CITY,
        7: SuperScraper.ZIP_CODE,
    }
    for idx, val in fill_plan.items():
        if idx < len(visible):
            await visible[idx].type_text(val)
    await asyncio.sleep(0.3)

    await _typeahead(tab, "country", "United States")
    await asyncio.sleep(1)
    await _typeahead(tab, "state", SuperScraper.STATE)
    await asyncio.sleep(1)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        submit_btn = await tab.find(tag_name="button", type="submit", raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
        return

    captcha_field = await tab.find(name="captchacode", raise_exc=False)
    if captcha_field:
        await captcha_field.scroll_into_view()
    print(f"\nForm filled for '{label}'. Enter the 6-digit CAPTCHA code shown, then press Enter.")
    code = input("CAPTCHA code: ").strip()
    if captcha_field:
        await captcha_field.type_text(code)
    await asyncio.sleep(0.3)

    submit_btn = await tab.find(tag_name="button", type="submit", raise_exc=False)
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(5)

    print(f"Submitted '{label}' for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            entries = RIGHT_MAP[right]
            for right_label_text, label in (entries if isinstance(entries, list) else [entries]):
                await _submit_request(tab, right_label_text, label, super_scraper)


asyncio.run(main())
