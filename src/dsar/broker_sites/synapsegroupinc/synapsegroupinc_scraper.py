# synapsegroupinc.com — OneTrust CDN DSAR webform
# (privacyportalde-cdn.onetrust.com/dsarwebform). The portal's own copy says it
# "has been developed to allow California users to submit a request", and the
# only residency question is a required "Are you a California Resident?" Yes/No.
# There is no path for a non-CA resident, so "Yes" is selected ONLY when the
# configured STATE is California; for any other state the question is left
# unanswered (we do not claim a residency we do not have) and must be handled
# manually.
#
#   requestTypesDSARElement  role="option" group, single-select (one submission
#       per right): "Request a Copy of My Personal Information" (Access) +
#       "Request More Information about How Synapse Processes My Personal
#       Information" (both RIGHT_TO_ACCESS); "Request Deletion of My Personal
#       Information" (RIGHT_TO_DELETE). Which run is decided ONLY by
#       SuperScraper.rights_to_exercise(RIGHT_MAP).
#   firstNameDSARElement / lastNameDSARElement / emailDSARElement
#   addressDSARElement / formField20DSARElement (line 2) / cityDSARElement /
#       formField17DSARElement (state) / zipDSARElement  — labelled "Required
#       for print subscribers only"; filled anyway from the persona.
#   "Are you a California Resident?" Yes/No role="option" -> "Yes" only for California
# reCAPTCHA gates submit — filled to that point.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = (
    "https://privacyportalde-cdn.onetrust.com/dsarwebform/"
    "2159c482-749a-49db-916b-475017a9efa5/855e3b71-3dd3-4546-977c-88c7430ade09.html"
)

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [
        ("Request a Copy of My Personal Information", "access"),
        ("Request More Information about How Synapse Processes My Personal Information", "info"),
    ],
    Right.RIGHT_TO_DELETE: [("Request Deletion of My Personal Information", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every option in the request-type group, as displayed -> the Right it maps to.
PAGE_RIGHTS = {
    "Request a Copy of My Personal Information": Right.RIGHT_TO_ACCESS,
    "Request More Information about How Synapse Processes My Personal Information": Right.RIGHT_TO_ACCESS,
    "Request Deletion of My Personal Information": Right.RIGHT_TO_DELETE,
}
RIGHTS_OPTIONS_CSS = "#requestTypesDSARElement [role='option']"

FIELD_XPATHS = {
    "First name": "//*[@id='firstNameDSARElement']",
    "Last name": "//*[@id='lastNameDSARElement']",
    "Email": "//*[@id='emailDSARElement']",
    "Address": "//*[@id='addressDSARElement']",
    "City": "//*[@id='cityDSARElement']",
    "State": "//*[@id='formField17DSARElement']",
    "Zip": "//*[@id='zipDSARElement']",
}


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

    if SuperScraper.HEALTH_CHECK:
        offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
        SuperScraper.audit_rights(offered, PAGE_RIGHTS)

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

    if (SuperScraper.STATE or "").strip().upper() == "CALIFORNIA":
        await _pick(tab, super_scraper, "Yes")  # "Are you a California Resident?"
    else:
        print(
            f"{super_scraper.OOPS} 'Are you a California Resident?' left unanswered — "
            f"STATE={SuperScraper.STATE!r}; this form only accepts California residents."
        )

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{tag}")
    print(f"'{right_label}' filled but NOT submitted — solve the reCAPTCHA manually, then Submit.")


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    requests = [entry for right in rights for entry in RIGHT_MAP[right]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right_label, tag in requests:
            await submit_request(tab, right_label, tag, super_scraper)


asyncio.run(main())
