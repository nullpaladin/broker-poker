# eyeota.com — Eyeota "Data Subject Request" form (eyeota.com/data-subject-request),
# a HubSpot form. Field ids carry a per-render GUID suffix, so everything is
# targeted by `name`.
# Fields: firstname, lastname, email; "nature_of_request" checkbox group
# (Access Request / Deletion / Update Request / HEM Opt-out / Opt-out /
# Questions / Complaints) — multi-select, one combined submission: Access
# Request + Opt-out + HEM Opt-out unconditionally; Deletion gated on
# REMOVE_INFORMATION; Update/Questions/Complaints skipped. "regulation" <select>
# has no Minnesota-applicable option (CCPA list is CA/CO/CT/VA/UT/NV only) —
# "Other / Generic" used. "message" textarea states the request.
# An invisible reCAPTCHA is present; it resolves without interaction.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://www.eyeota.com/data-subject-request"

RIGHTS = ["Access Request", "Opt-out", "HEM Opt-out"]
DELETE_RIGHT = "Deletion"


async def _set_text(tab, xpath, value):
    """Set an input/textarea via the native value setter + input/change events —
    HubSpot's React fields don't reliably accept click()+type here (a D&B cookie
    banner also overlaps the lower fields)."""
    el = await tab.find(xpath=xpath, raise_exc=False)
    if not el:
        return
    await el.execute_script(
        f"const p=this.tagName==='TEXTAREA'?window.HTMLTextAreaElement.prototype:window.HTMLInputElement.prototype;"
        f"const s=Object.getOwnPropertyDescriptor(p,'value').set; s.call(this,{value!r});"
        "this.dispatchEvent(new Event('input',{bubbles:true}));"
        "this.dispatchEvent(new Event('change',{bubbles:true}));"
        "this.dispatchEvent(new Event('blur',{bubbles:true}));"
    )
    await asyncio.sleep(0.2)


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        # dismiss the Dun & Bradstreet cookie banner that overlaps lower fields
        for label in ("Agree & Proceed", "Required Only"):
            btn = await tab.find(text=label, raise_exc=False)
            if btn:
                await btn.click()
                await asyncio.sleep(1)
                break

        for name, value in [
            ("firstname", SuperScraper.FIRST_NAME),
            ("lastname", SuperScraper.LAST_NAME),
            ("email", SuperScraper.EMAIL),
        ]:
            await _set_text(tab, f"//input[@name={name!r}]", value)

        rights = list(RIGHTS)
        if SuperScraper.REMOVE_INFORMATION:
            rights.append(DELETE_RIGHT)
        for value in rights:
            box = await tab.find(
                xpath=f"//input[@name='nature_of_request' and @value={value!r}]", raise_exc=False
            )
            if box:
                await box.execute_script("if (!this.checked) this.click();")
                await asyncio.sleep(0.1)

        reg = await tab.find(xpath="//select[@name='regulation']", raise_exc=False)
        if reg:
            await reg.execute_script(
                "const o=[...this.options].find(x=>x.value==='Other / Generic');"
                "if(o){const s=Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set;"
                "s.call(this,o.value);this.dispatchEvent(new Event('change',{bubbles:true}));}"
            )

        msg = (
            "I am a Minnesota resident exercising my privacy rights under the Minnesota "
            "Consumer Data Privacy Act. I request access to the personal information you "
            "hold about me and to opt out of the sale/sharing of my personal information "
            "and of targeted advertising (including any hashed-email / HEM based targeting)."
        )
        if SuperScraper.REMOVE_INFORMATION:
            msg += " I also request deletion of all personal information you hold about me."
        await _set_text(tab, "//textarea[@name='message']", msg)

        time.sleep(0.5)
        await SuperScraper.screenshot(tab, "resources/screenshots/eyeota_dry_run.png")
        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit privacy request for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
            )
            return

        submit = await tab.find(xpath="//input[@type='submit'] | //button[@type='submit']", raise_exc=False)
        if submit:
            await submit.click()
            await asyncio.sleep(3)
        source = await tab.page_source
        if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
            print(f"Submitted for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        else:
            print(f"{super_scraper.OOPS} Confirmation unclear — verify in browser")


asyncio.run(main())
