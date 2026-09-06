# upcell.io — "Request Removal" DSAR form on the /data-claim page (a Framer
# site). Fields: "First Name", "Last Name", "email", "phone number", and a
# "Request Type" <select> with options "Opt-Out / Delete My Information",
# "Data Access", "Other Privacy Request". One submission per request type:
# "Data Access" (access) + "Opt-Out / Delete My Information" (a combined
# opt-out+delete option) are both exercised. The many extra hidden text inputs
# (website / company / message / subject / ...) are spam-trap fields and are
# left blank. No CAPTCHA observed.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://www.upcell.io/data-claim"

REQUEST_TYPES = [
    ("Data Access", "access"),
    ("Opt-Out / Delete My Information", "optout_delete"),
]


async def submit_request(tab, request_type, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    for name, value in [
        ("First Name", SuperScraper.FIRST_NAME),
        ("Last Name", SuperScraper.LAST_NAME),
        ("email", SuperScraper.EMAIL),
        ("phone number", SuperScraper.PHONE_NUMBER),
    ]:
        field = await tab.find(xpath=f"//input[@name={name!r}]", raise_exc=False)
        if field:
            await field.type_text(value)
            await asyncio.sleep(0.2)

    sel = await tab.find(xpath="//select[@name='Request Type']", raise_exc=False)
    if sel:
        await sel.execute_script(
            f"const o=[...this.options].find(x=>x.text.trim()=={request_type!r});"
            "if(o){const s=Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set;"
            "s.call(this,o.value);this.dispatchEvent(new Event('change',{bubbles:true}));}"
        )

    time.sleep(0.5)
    await tab.take_screenshot(f"resources/screenshots/upcell_dry_run_{label}.png")
    print(f"Screenshot saved to resources/screenshots/upcell_dry_run_{label}.png")

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{request_type}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        return

    submit = await tab.find(text="SUBMIT", raise_exc=False)
    if submit:
        await submit.click()
        await asyncio.sleep(3)
    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted")):
        print(f"Submitted '{request_type}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{request_type}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,2000")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for request_type, label in REQUEST_TYPES:
            await submit_request(tab, request_type, label, super_scraper)


asyncio.run(main())
