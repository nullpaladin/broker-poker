# listkit.io — generic Termly DSAR form at app.termly.io/dsar/<uuid>.
# This deployment is the SIMPLER Termly variant — there is NO Access/Delete/
# Opt-out "action" radio group (unlike 01advertising.com's Termly form), so it
# is ONE combined submission with the requested rights spelled out in the
# "detail.content" textarea.
# Fields: "Website" (Termly template default "My Great New Website / App" — not
# editable to listkit's real name, left as served), name, email, identity_type
# radio ("personal"), a react-select combobox for the applicable law (options
# GDPR / CCPA / CPA / CTDPA / UCPA / VCDPA / OTHER — none Minnesota-specific,
# "OTHER" used), the detail.content textarea, and three "__doNotSubmit__.*"
# attestation checkboxes (perjury declaration, deletion is irreversible, email
# validation required) — all ticked by clicking their labels (setting .checked
# in JS doesn't register with Termly's React). No captcha; an emailed
# validation link is a normal post-submission step.
import asyncio
import time

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://app.termly.io/dsar/c4e44408-4a15-4dc3-9604-8cd01dd64998"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    rights = (
        "I am a Minnesota resident exercising my rights under the Minnesota Consumer "
        "Data Privacy Act. I request: (1) to know/access the personal information you "
        "hold about me, its sources and the parties it has been disclosed to; (2) to "
        "opt out of the sale and sharing of my personal information and of targeted "
        "advertising / profiling"
    )
    if SuperScraper.wants("delete"):
        rights += "; (3) deletion of all personal information you hold about me"
    rights += "."

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        name_field = await tab.find(xpath="//input[@name='name']", raise_exc=False)
        if name_field:
            await name_field.type_text(f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        email_field = await tab.find(xpath="//input[@name='email']", raise_exc=False)
        if email_field:
            await email_field.type_text(SuperScraper.EMAIL)

        personal = await tab.find(xpath="//input[@name='identity_type' and @value='personal']", raise_exc=False)
        if personal:
            await personal.execute_script("if (!this.checked) this.click();")

        combo = await tab.find(xpath="//input[@role='combobox']", raise_exc=False)
        if combo:
            await combo.click()
            await asyncio.sleep(0.5)
            option = await tab.find(text="OTHER", raise_exc=False)
            if option:
                await option.click()
                await asyncio.sleep(0.5)

        detail = await tab.find(xpath="//textarea[@name='detail.content']", raise_exc=False)
        if detail:
            await detail.type_text(rights)

        boxes = await tab.find(
            xpath="//input[starts-with(@name,'__doNotSubmit__')]", find_all=True, raise_exc=False
        ) or []
        for box in boxes:
            checked = await box.execute_script("return this.checked;")
            if not checked["result"]["result"]["value"]:
                # click the associated label (the input itself is visually hidden)
                await box.execute_script(
                    "const l=this.closest('label')||document.querySelector('label[for=\"'+this.id+'\"]');"
                    "(l||this).click();"
                )
                await asyncio.sleep(0.15)

        time.sleep(0.5)
        await SuperScraper.screenshot(tab, "resources/screenshots/listkit_dry_run.png")
        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit combined privacy request for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
            )
            return

        submit = await tab.find(text="SUBMIT", raise_exc=False)
        if submit:
            await submit.click()
            await asyncio.sleep(2)
            print(f"Submitted for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        else:
            print(f"{super_scraper.OOPS} SUBMIT button not found")


asyncio.run(main())
