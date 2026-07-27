# malvernmedia.com — PrivacyPillar Angular DSAR portal.
# Subject type: radio name="subjecttype", ID="Other US State Resident".
# Request type: radio name="requesttype" — single-select, one submission per right.
# Fields: email (type=email), first_name, last_name, country (typeahead name=country),
#   address, city, state (typeahead name=state), zip.
# Visible text input order: [0]=agency_email(skip), [1]=first, [2]=last,
#   [3]=country(named), [4]=address, [5]=city, [6]=state(named), [7]=zip.
# CAPTCHA: name="captchacode", 6-character alphanumeric image — manual entry in live mode.
# Always: Right to Know, Right to Correct, Right to Opt-Out (Sale/Sharing),
#   Right to Opt-Out (Cross-Behavioral Sale/Sharing), Right to Limit Sensitive PI.
# Gated on REMOVE_INFORMATION: Right to Delete.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = (
    "https://privacyportal.privacypillar.com/dsar/form"
    "?formid=6e6ff4b8-2296-4589-ae7f-563fa743ec2d"
    "&orgid=369c8ff9-8ffb-4308-8362-f01691e77db8"
    "&propid=64c8904f-8bac-4dd9-8e6c-d052be1918a2"
    "&status=publish"
)

ALWAYS_REQUESTS = [
    ("Right to Know", "know"),
    ("Right to Correct", "correct"),
    ("Right to Opt-Out of the Sale or Sharing of Personal Information", "optout_sale"),
    ("Right to Opt-Out of Cross-Behavioral Sale or Sharing", "optout_crossbehavioral"),
    ("Right to Limit Use and Disclosure of Sensitive Personal Information", "limit_sensitive"),
]
DELETE_REQUEST = ("Right to Delete", "delete")
# Tuple: (label_text_for_radio, short_label_for_filenames)


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
    time.sleep(0.5)

    req_lbl = await tab.find(text=right_label_text, raise_exc=False)
    if req_lbl:
        await req_lbl.click()
    else:
        print(f"{super_scraper.OOPS} Request type label '{right_label_text}' not found for {label}")
        return
    time.sleep(0.5)

    email_field = await tab.find(tag_name="input", type="email", raise_exc=False)
    if email_field:
        await email_field.type_text(SuperScraper.EMAIL)
    time.sleep(0.3)

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
    time.sleep(0.3)

    await _typeahead(tab, "country", "United States")
    await asyncio.sleep(1)
    await _typeahead(tab, "state", SuperScraper.STATE)
    await asyncio.sleep(1)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        submit_btn = await tab.find(tag_name="button", type="submit", raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await asyncio.sleep(1)
        await tab.take_screenshot(f"malvernmedia_dry_run_{label}.png")
        print(f"Screenshot saved to malvernmedia_dry_run_{label}.png")
        return

    captcha_field = await tab.find(name="captchacode", raise_exc=False)
    if captcha_field:
        await captcha_field.scroll_into_view()
    print(f"\nForm filled for '{label}'. Enter the 6-digit CAPTCHA code shown, then press Enter.")
    code = input("CAPTCHA code: ").strip()
    if captcha_field:
        await captcha_field.type_text(code)
    time.sleep(0.3)

    submit_btn = await tab.find(tag_name="button", type="submit", raise_exc=False)
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(5)

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{label}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{label}' — verify in browser")


async def main():
    options = ChromiumOptions()
    options.binary_location = "/snap/bin/chromium"
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,3000")
    super_scraper = SuperScraper()

    requests = list(ALWAYS_REQUESTS)
    if SuperScraper.REMOVE_INFORMATION:
        requests.append(DELETE_REQUEST)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right_id, label in requests:
            await _submit_request(tab, right_id, label, super_scraper)


asyncio.run(main())
