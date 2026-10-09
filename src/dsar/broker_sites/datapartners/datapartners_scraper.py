# datapartners.com — two separate Zoho CRM webforms (Zoho custom field ids
# like "CASECF1", "CASECF2" — opaque but stable across both pages): Access
# request (/information-access-request/) and Opt-Out request
# (/opt-out-request/). Required fields: Subject (free text, filled with a
# short description), Privacy Submitter (select: "Submitted by the
# Individual Requesting" used here), First Name (CASECF1), Last Name
# (CASECF2), Email, State (CASECF7). Optional: Phone, Address1 (CASECF3),
# City (CASECF5), Zip Code (CASECF6) — filled when available. The "2nd/3rd"
# variants of every field (for aliases) are left blank. Each page has its
# own BotDetect-style image CAPTCHA (name="enterdigest") requiring manual
# entry in live mode.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

ACCESS_URL = "https://www.datapartners.com/information-access-request/"
OPT_OUT_URL = "https://www.datapartners.com/opt-out-request/"


async def submit_request(tab, url, subject, super_scraper):
    await tab.go_to(url)
    await asyncio.sleep(5)

    subject_field = await tab.find(id="Subject", raise_exc=False)
    if subject_field:
        await subject_field.type_text(subject)

    submitter_select = await tab.find(id="CASECF17", raise_exc=False)
    if submitter_select:
        await submitter_select.execute_script(
            "for (var i=0;i<this.options.length;i++){"
            "  if(this.options[i].value==='Submitted by the Individual Requesting'){ this.selectedIndex=i; }"
            "}"
            "this.dispatchEvent(new Event('change', {bubbles:true}));"
        )

    fields = {
        "CASECF1": SuperScraper.FIRST_NAME,
        "CASECF2": SuperScraper.LAST_NAME,
        "Email": SuperScraper.EMAIL,
        "Phone": SuperScraper.PHONE_NUMBER,
        "CASECF3": SuperScraper.ADDRESS,
        "CASECF5": SuperScraper.CITY,
        "CASECF7": SuperScraper.STATE,
        "CASECF6": SuperScraper.ZIP_CODE,
    }
    for field_id, value in fields.items():
        if not value:
            continue
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)

    await asyncio.sleep(1)
    label = "".join(c if c.isalnum() else "_" for c in subject.lower())[:40].strip("_")
    await SuperScraper.screenshot(tab, f"resources/screenshots/datapartners_dry_run_{label}.png")
async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await submit_request(tab, ACCESS_URL, "Information Access Request", super_scraper)
        await submit_request(tab, OPT_OUT_URL, "Opt Out Request", super_scraper)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: forms filled for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}, not submitted")
            return

        print("\nBoth forms filled. Solve each page's image CAPTCHA and click Submit manually.")


asyncio.run(main())
