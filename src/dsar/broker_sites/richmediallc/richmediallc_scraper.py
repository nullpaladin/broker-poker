# richmediallc.com — custom (non-OneTrust) server-rendered "Privacy
# Request Form". "Request Type" is single-select (the page's own copy
# says to submit a separate request for each right) — one submission per
# right: Opt out of sale/share, Right to know, Right to delete (gated on
# REMOVE_INFORMATION). "Limit use of sensitive personal information" and
# "Correct inaccurate personal information" are skipped (no concrete
# sensitive-use limitation or inaccuracy to describe). Postal
# Address/City/Zip are optional (only relevant "if your request relates
# to postal marketing") — filled anyway since the data is available.
# Cloudflare Turnstile checkbox — **CAPTCHA solution required**.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://privacy.richmediallc.com/"

RIGHTS = ["opt_out_sale_share", "access_request"]
DELETE_RIGHT = "delete_request"

RIGHT_LABELS = {
    "opt_out_sale_share": "Opt out of sale/share",
    "access_request": "Right to know",
    "delete_request": "Right to delete",
}


async def submit_request(tab, right, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    fields = {
        "firstName": SuperScraper.FIRST_NAME,
        "lastName": SuperScraper.LAST_NAME,
        "email": SuperScraper.EMAIL,
        "postalAddress": SuperScraper.ADDRESS,
        "city": SuperScraper.CITY,
        "zipCode": SuperScraper.ZIP_CODE,
    }
    for field_id, value in fields.items():
        if not value:
            continue
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    state_select = await tab.find(id="state", raise_exc=False)
    if state_select:
        state_abbrev = SuperScraper.STATE_ABBREVIATED
        await state_select.execute_script(
            "for (var i=0;i<this.options.length;i++){"
            f"  if(this.options[i].value==={state_abbrev!r}){{ this.selectedIndex=i; }}"
            "}"
            "this.dispatchEvent(new Event('change', {bubbles:true}));"
        )
    else:
        print(f"{super_scraper.OOPS} State select not found")

    radio = await tab.find(xpath=f"//input[@name='requestType' and @value='{right}']", raise_exc=False)
    if radio:
        await radio.click()
    else:
        print(f"{super_scraper.OOPS} request type '{right}' not found")

    await asyncio.sleep(1)
    await tab.take_screenshot(path=f"resources/screenshots/richmediallc_dry_run_{right}.png")
    print(f"Screenshot saved to resources/screenshots/richmediallc_dry_run_{right}.png")
    print(
        f"\n'{RIGHT_LABELS[right]}' request filled but NOT submitted — a Cloudflare "
        "Turnstile checkbox requires a manual solve."
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
        for right in rights:
            await submit_request(tab, right, super_scraper)


asyncio.run(main())
