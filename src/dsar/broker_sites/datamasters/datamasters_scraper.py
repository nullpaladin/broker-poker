# datamasters.com (datamasters.org) — the /opt-out/ page's visible Formidable
# form is a "GET A QUOTE" sales form; the real privacy form is a LeadConnector
# (GoHighLevel) widget embedded in an iframe — navigate straight to it:
#   https://api.leadconnectorhq.com/widget/form/41dpCVPDaPkQi42RkPKk
# Fields: first_name (labelled "Name" — a full-name field), email, address,
# city, state, postal_code; a date field (YYYY-MM-DD, filled from DATE_OF_BIRTH)
# and a checkbox group (name="R3B5d3dOMvt84soqRzIF") — multi-select, one
# combined submission: "Request for access to all personal information" +
# "Opt out of the sale of personal information" unconditionally; "Request to
# delete all personal information" gated on REMOVE_INFORMATION;
# delete-some / categories / correct skipped.
# "Printed Name" is filled; "Signature" is a mouse-drawn canvas pad that is NOT
# automated (draw it manually), and "Verify Email" runs an email-verification
# step that needs a real inbox. reCAPTCHA + Cloudflare Turnstile also gate
# submission — form filled and left for a manual solve.
# **CAPTCHA solution required**
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://api.leadconnectorhq.com/widget/form/41dpCVPDaPkQi42RkPKk"

RIGHT_MAP = {
    "access": ["Request for access to all personal information"],
    "opt_out_sale_share": ["Opt out of the sale of personal information"],
    "delete": ["Request to delete all personal information"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


def _dob_iso():
    raw = (SuperScraper.DATE_OF_BIRTH or "").strip()
    for sep in ("/", "-", "."):
        if sep in raw:
            p = raw.split(sep)
            if len(p) == 3 and len(p[2]) == 4:
                return f"{p[2]}-{int(p[1]):02d}-{int(p[0]):02d}"
    return raw


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        for name, value in [
            ("first_name", f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}"),
            ("email", SuperScraper.EMAIL),
            ("address", SuperScraper.ADDRESS),
            ("city", SuperScraper.CITY),
            ("state", SuperScraper.STATE),
            ("postal_code", SuperScraper.ZIP_CODE),
        ]:
            await super_scraper.input_text_field(
                tab=tab, xpath=f"//input[@name={name!r}]", text=value, sleep=0.2
            )

        date_field = await tab.find(xpath="//input[@placeholder='YYYY - MM - DD']", raise_exc=False)
        if date_field:
            await date_field.type_text(_dob_iso())

        # "Printed Name" — the text input directly under the Signature canvas
        printed = await tab.find(
            xpath="//label[contains(., 'Printed Name')]/following::input[1]", raise_exc=False
        )
        if printed:
            await printed.type_text(f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")

        codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
        if not codes:
            print("No requested privacy rights apply to this form — nothing to do.")
            return
        rights = [entry for code in codes for entry in RIGHT_MAP[code]]
        for value in rights:
            box = await tab.find(
                xpath=f"//input[@type='checkbox' and starts-with(@value, {value[:35]!r})]", raise_exc=False
            )
            if box:
                await box.execute_script("if (!this.checked) this.click();")
                await asyncio.sleep(0.1)

        time.sleep(0.5)
        await SuperScraper.screenshot(tab, "resources/screenshots/datamasters_dry_run.png")
        print(
            "Request filled but NOT submitted — a reCAPTCHA / Cloudflare Turnstile must be "
            "solved manually before submitting."
        )

        if not SuperScraper.DRY_RUN:
            print("Solve the CAPTCHA, click Submit, then press Enter once confirmed...")
            input()


asyncio.run(main())
