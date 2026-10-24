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
#
# Page elements:
#   input[name=name] / input[name=email]       Name (full) / Email
#   input[name=identity_type][value=personal]  Identity type radio
#   input[role=combobox]                       "Applicable law" react-select -> "OTHER"
#   textarea[name="detail.content"]            Request details
#   input[name^="__doNotSubmit__"]             Three attestation checkboxes (ticked via their labels)
#   "SUBMIT" button (found by text)
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://app.termly.io/dsar/c4e44408-4a15-4dc3-9604-8cd01dd64998"

# One combined submission: every requested right is spelled out in the details textarea.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "detail.content",
    Right.RIGHT_TO_OPT_OUT: "detail.content",
    Right.RIGHT_TO_DELETE: "detail.content",
    Right.RIGHT_TO_LIST_OF_THIRD_PARTIES: "detail.content",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (A combined form with no rights chooser: the rights are spelled out in the details textarea.)

FIELD_XPATHS = {
    "Name": "//input[@name='name']",
    "Email": "//input[@name='email']",
    "Request details": "//textarea[@name='detail.content']",
}


async def main():
    super_scraper = SuperScraper()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    message = SuperScraper.request_statement(rights, broker="ListKit")

    options = SuperScraper.build_chromium_options()

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
            await js_utils.js_check(personal)

        # "Applicable law" react-select lists GDPR/CCPA/CPA/CTDPA/UCPA/VCDPA/OTHER —
        # no home-state option for most users, so "OTHER" is chosen regardless of
        # state (the request statement still names the state's actual law, if any).
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
            await detail.type_text(message)

        boxes = await tab.find(
            xpath="//input[starts-with(@name,'__doNotSubmit__')]", find_all=True, raise_exc=False
        ) or []
        for box in boxes:
            if not await js_utils.js_eval(box, "return this.checked;"):
                # click the associated label (the input itself is visually hidden)
                await box.execute_script(
                    "const l=this.closest('label')||document.querySelector('label[for=\"'+this.id+'\"]');"
                    "(l||this).click();"
                )
                await asyncio.sleep(0.15)

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        await asyncio.sleep(0.5)
        await SuperScraper.screenshot(tab, "dry_run")
        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit {[r.name for r in rights]} for {SuperScraper.EMAIL}")
            return

        submit = await tab.find(text="SUBMIT", raise_exc=False)
        if submit:
            await submit.click()
            await asyncio.sleep(2)
            print(f"Submitted {[r.name for r in rights]} for {SuperScraper.EMAIL} — confirm in the browser.")
        else:
            print(f"{super_scraper.OOPS} SUBMIT button not found")


asyncio.run(main())
