# datamasters.com (datamasters.org) — the /opt-out/ page's visible Formidable
# form is a "GET A QUOTE" sales form; the real privacy form is a LeadConnector
# (GoHighLevel) widget embedded in an iframe — navigate straight to it:
#   https://api.leadconnectorhq.com/widget/form/41dpCVPDaPkQi42RkPKk
# Rights the form exposes: access, opt-out of sale, delete (plus delete-some /
# categories / correct, which are skipped). Which of them run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). The checkbox group is multi-select, so
# all selected rights go out in one combined submission.
# "Signature" is a mouse-drawn canvas pad that is NOT automated (draw it manually),
# and "Verify Email" runs an email-verification step that needs a real inbox.
# reCAPTCHA + Cloudflare Turnstile also gate submission — form filled and left for
# a manual solve.
#
# Page elements:
#   input[name=first_name]        "Name" (full-name field)
#   input[name=email]             Email
#   input[name=address] / [name=city] / [name=state] / [name=postal_code]   Address fields
#   input[placeholder='YYYY - MM - DD']   Date field (filled from DATE_OF_BIRTH)
#   label "Printed Name" -> following input   Printed Name
#   input[name=R3B5d3dOMvt84soqRzIF]   Checkbox group of request types (see RIGHT_MAP)
# **CAPTCHA solution required**
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://api.leadconnectorhq.com/widget/form/41dpCVPDaPkQi42RkPKk"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Request for access to all personal information"],
    Right.RIGHT_TO_OPT_OUT: ["Opt out of the sale of personal information"],
    Right.RIGHT_TO_DELETE: ["Request to delete all personal information"],
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
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

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

        rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
        if not rights:
            print("No requested privacy rights apply to this form — nothing to do.")
            return
        entries = [entry for right in rights for entry in RIGHT_MAP[right]]
        for value in entries:
            box = await tab.find(
                xpath=f"//input[@type='checkbox' and starts-with(@value, {value[:35]!r})]", raise_exc=False
            )
            if box:
                await js_utils.js_check(box)
                await asyncio.sleep(0.1)

        time.sleep(0.5)
        await SuperScraper.screenshot(tab, "dry_run")
        print(
            "Request filled but NOT submitted — a reCAPTCHA / Cloudflare Turnstile must be "
            "solved manually before submitting."
        )

        if not SuperScraper.DRY_RUN:
            print("Solve the CAPTCHA, click Submit, then press Enter once confirmed...")
            input()


asyncio.run(main())
