# fmadata.com — /opt-out-requests/new Rails-rendered form, POSTs in place.
# One submission per right via the opt_out_request[request_type] <select>:
#   - "Opt out"    (opt_out)    -> Opt-Out   (unconditional)
#   - "Disclosure" (disclosure) -> Access     (unconditional)
#   - "Deletion"   (deletion)   -> Delete      (gated on REMOVE_INFORMATION)
# Fields: opt_out_request[name] (full name), [street_address], [city], [state],
# [postal_code]; is_authorized_agent radio -> "false"; [authorized_agent_name]
# left blank. Note: this form has NO email field. Ends in an hCaptcha widget —
# filled to that point and left for a manual solve + Submit.
# **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://www.fmadata.com/opt-out-requests/new"

RIGHTS = [
    ("opt_out", "opt_out"),
    ("disclosure", "access"),
]
DELETE_RIGHT = ("deletion", "delete")


async def _select_by_value(select_element, value):
    await select_element.execute_script(
        "for (var i=0;i<this.options.length;i++){"
        f"  if(this.options[i].value==={value!r}){{ this.selectedIndex=i; }}"
        "}"
        "this.dispatchEvent(new Event('change', {bubbles:true}));"
    )


async def submit_request(tab, request_type, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(4)

    rt = await tab.find(id="opt_out_request_request_type", raise_exc=False)
    if not rt:
        print(f"{super_scraper.OOPS} request_type select not found")
        return
    await _select_by_value(rt, request_type)
    await asyncio.sleep(0.3)

    full_name = " ".join(p for p in (SuperScraper.FIRST_NAME, SuperScraper.LAST_NAME) if p)
    state_value = SuperScraper.STATE
    fields = {
        "opt_out_request_name": full_name,
        "opt_out_request_street_address": SuperScraper.ADDRESS,
        "opt_out_request_city": SuperScraper.CITY,
        "opt_out_request_state": state_value,
        "opt_out_request_postal_code": SuperScraper.ZIP_CODE,
    }
    for field_id, val in fields.items():
        if not val:
            continue
        el = await tab.find(id=field_id, raise_exc=False)
        if el:
            await el.type_text(val)
            await asyncio.sleep(0.15)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    agent_no = await tab.find(id="opt_out_request_is_authorized_agent_false", raise_exc=False)
    if agent_no:
        await agent_no.click()
    else:
        print(f"{super_scraper.OOPS} authorized-agent 'No' radio not found")

    await asyncio.sleep(1)
    await tab.take_screenshot(path=f"resources/screenshots/fmadata_dry_run_{label}.png")
    print(f"Screenshot saved to resources/screenshots/fmadata_dry_run_{label}.png")
    print(
        f"'{request_type}' request filled but NOT submitted — solve the hCaptcha "
        f"manually, then click Submit."
    )


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
        for request_type, label in rights:
            await submit_request(tab, request_type, label, super_scraper)


asyncio.run(main())
