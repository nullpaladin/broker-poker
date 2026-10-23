# sourceitmarketing.com — /privacy/ has two forms; the DSAR one is the "contact"
# form (action=.../index.php?action=contact). Server-rendered, POSTs in place.
# One submission per "Subject" <select>:
#   "Request to know or access what personal information we are collecting" -> Access
#   "Opt out of sale or sharing of personal information"                   -> Opt-Out
#   "Delete personal information"                                          -> Delete

#   "Request to know what we are selling ... and to whom" / "limit sensitive"
#   / "Other" are skipped as non-core.
# Page elements:
#   select[name=subject]   "Subject" <select> (options above)
#   contactemail          Reply email
#   removeaddress         Email(s) to investigate/remove (the persona email)
#   textarea[name=comments]  Request text
#   isca1 checkbox        "resident of California ..." — left unchecked (we are not CA residents)
# hCaptcha gates the submit — filled to that point.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper
from src.dsar import js_utils

URL = "https://sourceitmarketing.com/privacy/"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("Request to know or access what personal information we are collecting", "access")],
    Right.RIGHT_TO_OPT_OUT: [("Opt out of sale or sharing of personal information", "opt_out")],
    Right.RIGHT_TO_DELETE: [("Delete personal information", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
RIGHTS_OPTIONS_CSS = "select[name='subject'] option"  # three of the six option texts are truncated in the notes

FIELD_XPATHS = {
    "Subject": "//select[@name='subject']",
    "Reply email": "//input[@name='contactemail']",
    "Email to investigate": "//input[@name='removeaddress']",
    "Comments": "//textarea[@name='comments']",
}


async def submit_request(tab, right_label, right, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    # The DSAR form is the one containing the "Subject" <select name="subject">.
    if SuperScraper.HEALTH_CHECK:
        offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
        SuperScraper.audit_rights(offered, PAGE_RIGHTS)

    subject = await tab.find(xpath="//select[@name='subject']", raise_exc=False)
    if not subject:
        print(f"{super_scraper.OOPS} 'Subject' select not found")
        return
    await js_utils.select_native_option(subject, text=right_label)
    await asyncio.sleep(0.4)

    form_xp = "//form[.//select[@name='subject']]"
    for name, val in (
        ("contactemail", SuperScraper.EMAIL),
        ("removeaddress", SuperScraper.EMAIL),
    ):
        el = await tab.find(xpath=f"{form_xp}//input[@name={name!r}]", raise_exc=False)
        if el:
            await el.type_text(val)
            await asyncio.sleep(0.15)
        else:
            print(f"{super_scraper.OOPS} field '{name}' not found")

    comments = await tab.find(xpath=f"{form_xp}//textarea[@name='comments']", raise_exc=False)
    if comments:
        await comments.type_text(
            SuperScraper.request_statement([right], broker="Source IT Marketing")
        )

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
    print(f"'{right_label}' filled but NOT submitted — solve the hCaptcha manually, then Submit.")


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    requests = [(entry[0], right) for right in rights for entry in RIGHT_MAP[right]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right_label, right in requests:
            await submit_request(tab, right_label, right, super_scraper)


asyncio.run(main())
