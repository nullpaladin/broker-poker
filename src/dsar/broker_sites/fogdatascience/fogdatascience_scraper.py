# fogdatascience.com — /opt-out "Submit a California Privacy Request" form
# (Squarespace form block). The separate "Opt-Out My Device" mini-form on the
# same page is not used; this broader form covers the same ground plus Access/
# Delete/etc.
#   fname / lname / email (required)
#   "Message" textarea (required) -> the request, in words
#   "Mobile Advertising ID" textarea (required) -> the MAID
#   "Identifier" text -> also the MAID
#   a Yes/No checkbox pair (residency/attestation) -> "Yes"
#   a rights checkbox group -> "Right to Know" + "Right to Access" + "Right to
#       Opt-out" unconditionally; "Right to Delete" gated on REMOVE_INFORMATION;
#       "Right to Limit" skipped.
# reCAPTCHA Enterprise gates submit — filled to that point.
# **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://www.fogdatascience.com/opt-out"

RIGHTS = ["Right to Know", "Right to Access", "Right to Opt-out"]
DELETE_RIGHT = "Right to Delete"

REQUEST_TEXT = (
    "I am exercising my applicable state privacy rights with respect to the "
    "commercially available device location data associated with the mobile "
    "advertising ID below: the right to know/access what you have, and the "
    "right to opt out of its sale or sharing."
)


async def _check_by_text(tab, super_scraper, text):
    for xp in (
        f"//label[normalize-space()={text!r}]//input[@type='checkbox']",
        f"//label[normalize-space()={text!r}]/preceding-sibling::input[@type='checkbox'][1]",
        f"//*[normalize-space(text())={text!r}]/ancestor::*[self::label or contains(@class,'option')][1]//input[@type='checkbox']",
        f"//input[@type='checkbox'][following-sibling::*[normalize-space()={text!r}]]",
    ):
        el = await tab.find(xpath=xp, raise_exc=False)
        if el:
            await el.click()
            await asyncio.sleep(0.2)
            return True
    print(f"{super_scraper.OOPS} checkbox for {text!r} not found")
    return False


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(7)

        # dismiss cookie banner if present
        await tab.execute_script(
            "var b=[...document.querySelectorAll('button')].find(x=>/accept all/i.test(x.textContent));"
            "if(b)b.click();"
        )
        await asyncio.sleep(1)

        for xp, value in (
            ("//input[@name='fname']", SuperScraper.FIRST_NAME),
            ("//input[@name='lname']", SuperScraper.LAST_NAME),
            ("//input[@type='email']", SuperScraper.EMAIL),
        ):
            el = await tab.find(xpath=xp, raise_exc=False)
            if el:
                await el.type_text(value)
                await asyncio.sleep(0.2)
            else:
                print(f"{super_scraper.OOPS} field {xp} not found")

        msg = await tab.find(xpath="//textarea[@id='textarea-f01c0ab9-6bb9-48dd-bb97-f71512d2160d-field']", raise_exc=False)
        if not msg:
            msg = await tab.find(xpath="(//textarea)[1]", raise_exc=False)
        if msg:
            await msg.type_text(REQUEST_TEXT)

        maid = await tab.find(xpath="//textarea[@id='textarea-2a4cf7b5-c8d3-40e4-96be-ead3ca4acd7e-field']", raise_exc=False)
        if not maid:
            maid = await tab.find(xpath="(//textarea)[2]", raise_exc=False)
        if maid and SuperScraper.ADVERTISING_ID:
            await maid.type_text(SuperScraper.ADVERTISING_ID)

        ident = await tab.find(xpath="//input[@id='text-471c630a-7cfc-4491-a8b6-3cbd62e41e7e-field']", raise_exc=False)
        if ident and SuperScraper.ADVERTISING_ID:
            await ident.type_text(SuperScraper.ADVERTISING_ID)

        await _check_by_text(tab, super_scraper, "Yes")

        rights = list(RIGHTS)
        if SuperScraper.REMOVE_INFORMATION:
            rights.append(DELETE_RIGHT)
        for r in rights:
            await _check_by_text(tab, super_scraper, r)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/fogdatascience_dry_run.png", beyond_viewport=True)
        print("Request filled but NOT submitted — solve the reCAPTCHA manually, then Submit.")


asyncio.run(main())
