# hibu.com DSAR scraper — exercises Right to Access, Opt-Out (Sale/Share), and
# Right to Delete (gated on REMOVE_INFORMATION). "Correct my Personal Information"
# is available on the site but requires specifying what to correct; skipped here.
# Server-rendered HTML POST form, no captcha. Visitor type always set to
# "Visitor / User of hibu.com or yellowbook.com". Submits once per request type.
import asyncio
import json

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://hibu.com/legal/privacy-form"

VISITOR_TYPE = "Visitor / User of hibu.com or yellowbook.com"

REQUESTS = [
    ("Access to my Personal Information", "access"),
    ("Opt-out from the Sale or Share of Personal Information", "optout"),
]
DELETE_REQUEST = ("Deletion of my Personal Information", "delete")


def _js_set_id(field_id, value):
    fid = json.dumps(field_id)
    val = json.dumps(str(value))
    return (
        f"(function(){{"
        f"var el=document.getElementById({fid});"
        f"if(!el)return;"
        f"el.value={val};"
        f"el.dispatchEvent(new Event('input',{{bubbles:true}}));"
        f"el.dispatchEvent(new Event('change',{{bubbles:true}}));"
        f"}})();"
    )


async def submit_request(tab, request_type, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    await tab.execute_script(
        "var btn=document.getElementById('onetrust-accept-btn-handler');"
        "if(btn)btn.click();"
    )
    await asyncio.sleep(1)

    await tab.execute_script(_js_set_id("form-eng-US-3571-91576_fields_201064", VISITOR_TYPE))
    await tab.execute_script(_js_set_id("form-eng-US-3571-91576_fields_201067", request_type))
    await tab.execute_script(_js_set_id("form-eng-US-3571-91576_fields_201070", SuperScraper.FIRST_NAME))
    await tab.execute_script(_js_set_id("form-eng-US-3571-91576_fields_201073", SuperScraper.LAST_NAME))
    await tab.execute_script(_js_set_id("form-eng-US-3571-91576_fields_201076", SuperScraper.EMAIL))
    await tab.execute_script(_js_set_id("form-eng-US-3571-91576_fields_201079", SuperScraper.STATE))

    await tab.execute_script(
        "var cb=document.getElementById('form-eng-US-3571-91576_fields_201091_0');"
        "if(cb&&!cb.checked)cb.click();"
    )

    await asyncio.sleep(1)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{request_type}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        await SuperScraper.screenshot(tab, f"resources/screenshots/hibu_dry_run_{label}.png")
        return

    await tab.execute_script(
        "document.getElementById('form-eng-US-3571-91576_fields_201097').click();"
    )
    await asyncio.sleep(5)

    text = await tab.execute_script("return document.body.innerText") or ""
    if isinstance(text, dict):
        text = text.get("result", {}).get("result", {}).get("value", "")
    if any(w in text.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{request_type}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{request_type}' — verify in browser")


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
        for request_type, label in requests:
            await submit_request(tab, request_type, label, super_scraper)


asyncio.run(main())
