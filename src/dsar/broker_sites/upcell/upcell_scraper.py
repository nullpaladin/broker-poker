# upcell.io — "Request Removal" DSAR form on the /data-claim page (a Framer
# site). Fields: "First Name", "Last Name", "email", "phone number", and a
# "Request Type" <select> with options "Opt-Out / Delete My Information",
# "Data Access", "Other Privacy Request". One submission per request type:
# "Data Access" (access) and "Opt-Out / Delete My Information" (a combined
# opt-out+delete option, so mapped to both opt-out and delete; submitted once).
# Which run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP). The many extra hidden text inputs
# (website / company / message / subject / ...) are spam-trap fields and are
# left blank. No CAPTCHA observed.
#
# Page elements:
#   input[name="First Name"] / input[name="Last Name"]   First / Last name
#   input[name="email"]                                  Email
#   input[name="phone number"]                           Phone number
#   select[name="Request Type"]                          "Request Type" (see RIGHT_MAP)
#   "SUBMIT" button
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.upcell.io/data-claim"

# Right -> "Request Type" option. Opt-out and delete share one combined option.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Data Access",
    Right.RIGHT_TO_OPT_OUT: "Opt-Out / Delete My Information",
    Right.RIGHT_TO_DELETE: "Opt-Out / Delete My Information",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, right, request_type, super_scraper):
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
    await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{request_type}' ({right.name}) for {SuperScraper.EMAIL}")
        return

    submit = await tab.find(text="SUBMIT", raise_exc=False)
    if submit:
        await submit.click()
        await asyncio.sleep(3)
    print(f"Submitted '{request_type}' ({right.name}) for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    # Opt-out and delete share one option: submit each distinct request type once.
    seen = {}
    for right in rights:
        seen.setdefault(RIGHT_MAP[right], right)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for request_type, right in seen.items():
            await submit_request(tab, right, request_type, super_scraper)


asyncio.run(main())
