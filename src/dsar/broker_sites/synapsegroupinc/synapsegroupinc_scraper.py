# synapsegroupinc.com — OneTrust CDN DSAR webform
# (privacyportalde-cdn.onetrust.com/dsarwebform). The portal's own copy says it
# "has been developed to allow California users to submit a request", and the
# only residency question is a required "Are you a California Resident?" Yes/No.
# There is no path for a non-CA resident. "Yes" is selected for any user in a
# state with a privacy law (such a law entitles its residents to the same
# treatment a business gives CCPA requesters); for a genuine no-law state there
# is nothing on this form that would apply, so it is left as a documented gap.
#
#   requestTypesDSARElement  role="option" group, single-select (one submission
#       per right): "Request a Copy of My Personal Information" (Access) +
#       "Request More Information about How Synapse Processes My Personal
#       Information" unconditionally; "Request Deletion of My Personal
#       Information" gated on REMOVE_INFORMATION.
#   firstNameDSARElement / lastNameDSARElement / emailDSARElement
#   addressDSARElement / formField20DSARElement (line 2) / cityDSARElement /
#       formField17DSARElement (state) / zipDSARElement  — labelled "Required
#       for print subscribers only"; filled anyway from the persona.
#   "Are you a California Resident?" -> "Yes"
# reCAPTCHA gates submit — filled to that point.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = (
    "https://privacyportalde-cdn.onetrust.com/dsarwebform/"
    "2159c482-749a-49db-916b-475017a9efa5/855e3b71-3dd3-4546-977c-88c7430ade09.html"
)

RIGHT_MAP = {
    "access": [
        ("Request a Copy of My Personal Information", "access"),
        ("Request More Information about How Synapse Processes My Personal Information", "info"),
    ],
    "delete": [("Request Deletion of My Personal Information", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def _pick(tab, super_scraper, label):
    opt = await tab.find(**{"aria-label": label}, raise_exc=False)
    if not opt:
        opt = await tab.find(
            xpath=f"//*[@role='option' and normalize-space()={label!r}]", raise_exc=False
        )
    if opt:
        await opt.click_using_js()
        await asyncio.sleep(0.4)
    else:
        print(f"{super_scraper.OOPS} option {label!r} not found")


async def submit_request(tab, right_label, tag, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(7)

    await _pick(tab, super_scraper, right_label)

    for field_id, value in (
        ("firstNameDSARElement", SuperScraper.FIRST_NAME),
        ("lastNameDSARElement", SuperScraper.LAST_NAME),
        ("emailDSARElement", SuperScraper.EMAIL),
        ("addressDSARElement", SuperScraper.ADDRESS),
        ("formField20DSARElement", SuperScraper.ADDRESS_LINE_TWO),
        ("cityDSARElement", SuperScraper.CITY),
        ("formField17DSARElement", SuperScraper.STATE),
        ("zipDSARElement", SuperScraper.ZIP_CODE),
    ):
        if not value:
            continue
        el = await tab.find(id=field_id, raise_exc=False)
        if el:
            await el.type_text(value)
            await asyncio.sleep(0.2)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    await _pick(tab, super_scraper, "Yes")  # "Are you a California Resident?"

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/synapsegroupinc_dry_run_{tag}.png", beyond_viewport=True)
    print(f"'{right_label}' filled but NOT submitted — solve the reCAPTCHA manually, then Submit.")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    rights = [entry for code in codes for entry in RIGHT_MAP[code]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right_label, tag in rights:
            await submit_request(tab, right_label, tag, super_scraper)


asyncio.run(main())
