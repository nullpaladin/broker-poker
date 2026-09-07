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

RIGHTS = [
    ("Request to know or access what personal information we are collecting", "access"),
    ("Opt out of sale or sharing of personal information", "opt_out"),
]
DELETE_RIGHT = ("Delete personal information", "delete")


async def _select_by_text(select_element, text):
    await select_element.execute_script(
        "for (var i=0;i<this.options.length;i++){"
        f"  if(this.options[i].text.trim()==={text!r}){{ this.selectedIndex=i; }}"
        "}"
        "this.dispatchEvent(new Event('change', {bubbles:true}));"
    )


async def submit_request(tab, right_label, tag, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    # The DSAR form is the one containing the "Subject" <select name="subject">.
    subject = await tab.find(xpath="//select[@name='subject']", raise_exc=False)
    if not subject:
        print(f"{super_scraper.OOPS} 'Subject' select not found")
        return
    await _select_by_text(subject, right_label)
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
    await tab.take_screenshot(path=f"resources/screenshots/sourceitmarketing_dry_run_{tag}.png", beyond_viewport=True)
    print(f"Screenshot saved to resources/screenshots/sourceitmarketing_dry_run_{tag}.png")
    print(f"'{right_label}' filled but NOT submitted — solve the hCaptcha manually, then Submit.")


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
        for right_label, tag in rights:
            await submit_request(tab, right_label, tag, super_scraper)


asyncio.run(main())
