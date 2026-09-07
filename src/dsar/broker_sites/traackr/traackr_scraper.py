# traackr.com — /data-opt-out embeds a Formsite form via an iframe with a
# real, populated `src` (reachable via `tab.get_frame()`, same technique as
# realsourcedata.com's Tally.so embed elsewhere in this repo). "Type of data
# request" is a native single-select (Access/Deletion/Rectification) — one
# submission per right: Access unconditionally, Deletion gated on
# REMOVE_INFORMATION; Rectification skipped (no concrete inaccuracy). No
# CAPTCHA. IMPORTANT GAP: the form requires "at least one Twitter, Instagram,
# or Facebook Handle/URL" to validate identity — Traackr identifies people by
# social media presence, not name/email alone, and this repo's SuperScraper
# has no social-handle fields (only LINKEDIN_URL, which isn't one of the
# accepted platforms). That field is left blank; the form will likely reject
# submission without it. Everything else is filled and, since there's no
# CAPTCHA, DRY_RUN is otherwise respected for the parts that can be supplied.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.traackr.com/data-opt-out"

RIGHTS = [("Radio-0", "access")]
DELETE_RIGHT = ("Radio-1", "delete")


async def submit_request(tab, request_type_value, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    iframe_element = await tab.find(tag_name="iframe", raise_exc=False)
    if not iframe_element:
        print(f"{super_scraper.OOPS} Formsite iframe not found")
        return
    frame = await tab.get_frame(iframe_element)
    await asyncio.sleep(2)

    request_type_select = await frame.find(id="RESULT_RadioButton-0", raise_exc=False)
    if request_type_select:
        await request_type_select.execute_script(
            "for (var i=0;i<this.options.length;i++){"
            f"  if(this.options[i].value==={request_type_value!r}){{ this.selectedIndex=i; }}"
            "}"
            "this.dispatchEvent(new Event('change', {bubbles:true}));"
        )
    else:
        print(f"{super_scraper.OOPS} Request type select not found")

    fields = {
        "RESULT_TextField-1": SuperScraper.FIRST_NAME,
        "RESULT_TextField-2": SuperScraper.LAST_NAME,
        "RESULT_TextField-3": SuperScraper.EMAIL,
        "CONFIRM_TextField-3": SuperScraper.EMAIL,
    }
    for field_id, value in fields.items():
        field = await frame.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/traackr_dry_run_{label}.png")
    print(
        "\nNo Twitter/Instagram/Facebook handle was supplied (SuperScraper has no social-handle "
        "fields) — the form requires at least one to validate identity, so submission will "
        "likely be rejected even in live mode."
    )

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would attempt to submit '{label}' request for {SuperScraper.EMAIL}")
        return

    submit_button = await frame.find(id="FSsubmit", raise_exc=False)
    if submit_button:
        await submit_button.click()
        await asyncio.sleep(3)
        print(f"Attempted to submit '{label}' request for {SuperScraper.EMAIL}")
    else:
        print(f"{super_scraper.OOPS} submit button not found")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    rights = list(RIGHTS)
    if SuperScraper.REMOVE_INFORMATION:
        rights.append(DELETE_RIGHT)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for request_type_value, label in rights:
            await submit_request(tab, request_type_value, label, super_scraper)


asyncio.run(main())
