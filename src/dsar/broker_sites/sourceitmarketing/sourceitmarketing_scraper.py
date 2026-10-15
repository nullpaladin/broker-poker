# sourceitmarketing.com — /privacy/ has two forms; the DSAR one is the "contact"
# form (action=.../index.php?action=contact). Server-rendered, POSTs in place.
# One submission per "Subject" <select>:
#   "Request to know or access what personal information we are collecting" -> Access
#   "Opt out of sale or sharing of personal information"                   -> Opt-Out
#   "Delete personal information"                                          -> Delete
#       (gated on REMOVE_INFORMATION)
#   "Request to know what we are selling ... and to whom" / "limit sensitive"
#   / "Other" are skipped as non-core.
# Fields: contactemail (reply email), removeaddress (email(s) to investigate/
#   remove — the persona email), comments (the request, in words), isca1
#   checkbox ("resident of California ..." — left unchecked; persona is MN).
# hCaptcha gates the submit — filled to that point.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://sourceitmarketing.com/privacy/"

RIGHT_MAP = {
    "access": [("Request to know or access what personal information we are collecting", "access")],
    "opt_out_sale_share": [("Opt out of sale or sharing of personal information", "opt_out")],
    "delete": [("Delete personal information", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, right_label, tag, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    # The DSAR form is the one containing the "Subject" <select name="subject">.
    subject = await tab.find(xpath="//select[@name='subject']", raise_exc=False)
    if not subject:
        print(f"{super_scraper.OOPS} 'Subject' select not found")
        return
    await SuperScraper.select_native_option(subject, text=right_label)
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
            f"I am exercising the following right: {right_label}. Please process this "
            f"request for the personal information associated with {SuperScraper.EMAIL}."
        )

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/sourceitmarketing_dry_run_{tag}.png", beyond_viewport=True)
    print(f"'{right_label}' filled but NOT submitted — solve the hCaptcha manually, then Submit.")


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
