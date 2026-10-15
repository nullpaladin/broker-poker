# fogdatascience.com — /opt-out "Submit a California Privacy Request" form
# (Squarespace form block). The separate "Opt-Out My Device" mini-form on the
# same page is not used; this broader form covers the same ground plus Access/
# Delete/etc.
#   fname / lname / email (required)
#   "Message" textarea (required) -> the request, in words
#   "Mobile Advertising ID" textarea (required) -> the MAID
#   "Identifier" text -> also the MAID
#   a Yes/No checkbox pair (residency/attestation) -> "Yes"
#   a rights checkbox group -> "Right to Know" + "Right to Access" (Access),
#       "Right to Opt-out" (Opt-Out), "Right to Delete" (Delete);
#       "Right to Limit" is offered but not automated.
# reCAPTCHA Enterprise gates submit — filled to that point.
# **CAPTCHA solution required**
#
# Page elements:
#   input[name=fname] / input[name=lname] / input[type=email]   First / Last name / Email
#   textarea-f01c0ab9-...-field    "Message" textarea (fallback: first textarea)
#   textarea-2a4cf7b5-...-field    "Mobile Advertising ID" textarea (fallback: second textarea)
#   text-471c630a-...-field        "Identifier" text input
#   "Yes" checkbox                 Yes/No checkbox pair
#   rights checkboxes, by label text (see RIGHT_MAP)
#   "Accept all" cookie button
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.fogdatascience.com/opt-out"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Right to Know", "Right to Access"],
    Right.RIGHT_TO_OPT_OUT: ["Right to Opt-out"],
    Right.RIGHT_TO_DELETE: ["Right to Delete"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

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
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()

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
            await msg.type_text(
                SuperScraper.request_statement(rights, broker="Fog Data Science")
                + " This concerns the mobile advertising ID given below."
            )

        maid = await tab.find(xpath="//textarea[@id='textarea-2a4cf7b5-c8d3-40e4-96be-ead3ca4acd7e-field']", raise_exc=False)
        if not maid:
            maid = await tab.find(xpath="(//textarea)[2]", raise_exc=False)
        if maid and SuperScraper.ADVERTISING_ID:
            await maid.type_text(SuperScraper.ADVERTISING_ID)

        ident = await tab.find(xpath="//input[@id='text-471c630a-7cfc-4491-a8b6-3cbd62e41e7e-field']", raise_exc=False)
        if ident and SuperScraper.ADVERTISING_ID:
            await ident.type_text(SuperScraper.ADVERTISING_ID)

        await _check_by_text(tab, super_scraper, "Yes")

        for right in rights:
            for entry in RIGHT_MAP[right]:
                await _check_by_text(tab, super_scraper, entry)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run")
        print("Request filled but NOT submitted — solve the reCAPTCHA manually, then Submit.")


asyncio.run(main())
