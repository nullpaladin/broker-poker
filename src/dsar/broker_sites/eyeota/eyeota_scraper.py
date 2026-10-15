# eyeota.com — Eyeota "Data Subject Request" form (eyeota.com/data-subject-request),
# a HubSpot form. Field ids carry a per-render GUID suffix, so everything is
# targeted by `name`.
# Fields: firstname, lastname, email; "nature_of_request" checkbox group
# (Access Request / Deletion / Update Request / HEM Opt-out / Opt-out /
# Questions / Complaints) — multi-select, one combined submission: Access
# Request, Opt-out + HEM Opt-out, Deletion; Update/Questions/Complaints skipped
# (Update is not automatable). "regulation" <select>
# has no home-state option for most users (its list is CCPA-era only:
# CA/CO/CT/VA/UT/NV) so "Other / Generic" is used regardless of state.
# An invisible reCAPTCHA is present; it resolves without interaction.
#
# "HEM Opt-out": HEM = Hashed Email — a hash (e.g. SHA-256) of your email address
# that ad-tech vendors like Eyeota use as a persistent, cookieless identifier to
# recognise/target you across sites and devices without storing the raw email.
# "HEM based targeting" is ad targeting keyed off that hash; this dedicated
# checkbox (separate from the generic "Opt-out") asks Eyeota to stop using your
# hashed email for that identity resolution / targeting.
#
# Page elements (all by name):
#   input[name=firstname] / [name=lastname] / [name=email]   First / Last name / Email
#   input[name=nature_of_request]   "nature_of_request" checkbox group (values in RIGHT_MAP)
#   select[name=regulation]         "regulation" select -> "Other / Generic"
#   textarea[name=message]          Message
#   "Agree & Proceed" / "Required Only"   Dun & Bradstreet cookie banner buttons
#   input/button[type=submit]       Submit
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper
from src.dsar import js_utils

URL = "https://www.eyeota.com/data-subject-request"

# Right -> this form's "nature_of_request" checkbox value(s).
# "HEM Opt-out" rides along with the opt-out.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Access Request"],
    Right.RIGHT_TO_OPT_OUT: ["Opt-out", "HEM Opt-out"],
    Right.RIGHT_TO_DELETE: ["Deletion"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def _set_text(tab, xpath, value):
    """HubSpot's React fields don't reliably accept click()+type here (a D&B cookie
    banner also overlaps the lower fields), so set the value in JS."""
    el = await tab.find(xpath=xpath, raise_exc=False)
    if not el:
        return
    await js_utils.js_set_value(el, value, blur=True)
    await asyncio.sleep(0.2)


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

        checkbox_values = list(dict.fromkeys(v for r in rights for v in RIGHT_MAP[r]))
        for value in checkbox_values:
            box = await tab.find(
                xpath=f"//input[@name='nature_of_request' and @value={value!r}]", raise_exc=False
            )
            if box:
                await js_utils.js_check(box)
                await asyncio.sleep(0.1)

        reg = await tab.find(xpath="//select[@name='regulation']", raise_exc=False)
        if reg:
            await reg.execute_script(
                "const o=[...this.options].find(x=>x.value==='Other / Generic');"
                "if(o){const s=Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set;"
                "s.call(this,o.value);this.dispatchEvent(new Event('change',{bubbles:true}));}"
            )

        msg = SuperScraper.request_statement(rights, broker="Eyeota")
        if Right.RIGHT_TO_OPT_OUT in rights:
            msg += (" This includes any hashed-email / HEM based targeting or identity "
                    "resolution keyed off a hash of my email address.")
        await _set_text(tab, "//textarea[@name='message']", msg)

        time.sleep(0.5)

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, {
                "First name": "//input[@name='firstname']",
                "Last name": "//input[@name='lastname']",
                "Email": "//input[@name='email']",
                "Message": "//textarea[@name='message']",
            })

        await SuperScraper.screenshot(tab, "dry_run")
        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit {[r.name for r in rights]} for {SuperScraper.EMAIL}")
            return

        submit = await tab.find(xpath="//input[@type='submit'] | //button[@type='submit']", raise_exc=False)
        if submit:
            await submit.click()
            await asyncio.sleep(3)
        print(f"Submitted {[r.name for r in rights]} for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())
