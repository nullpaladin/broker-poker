# experian.com — Experian's consumer privacy portal
# (consumerprivacy.experian.com/request). A multi-step SPA wizard:
#   Step 1  select your state -> "Make a new request"
#   Step 2  tick the request type(s) you want -> "Continue"
#   Step 3+ identity details, then an identity-verification step (Experian is a
#           credit bureau, so this is a genuine ID/knowledge-based check)
# This scraper drives steps 1-2 (state = STATE, all request-type checkboxes
# ticked) and screenshots step 3; the identity + verification steps are left
# for the user because they require real, verifiable identity data that this
# repo's persona does not have. NOTE: some request-type paths hand off to
# crportal.tapad.com (Tapad is an Experian company — see the tapad.com entry).
#
# Page elements:
#   //select                         Step 1 state select (matched by visible state name)
#   "Make a new request"             Step 1 button
#   input[type=checkbox]             Step 2 request-type checkboxes (identified by nearby label text)
#       "Delete personal information"  the Delete checkbox
#   "Continue"                       Step 2 button
#   Step 3 inputs (found by label): First Name / Last Name / Date of Birth / Current Address /
#       ZIP Code / City / Phone Number / Email Address / Confirm Email Address
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper
from src.dsar import js_utils

URL = "https://consumerprivacy.experian.com/request"

DELETE_CHECKBOX_TEXT = "delete personal information"  # "Delete personal information"
OTHER_REQUESTS = "every request-type checkbox except Delete"

# Step 2 offers one checkbox per request type; only the Delete one is identified by name.
# All other checkboxes are ticked whenever the form runs.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: OTHER_REQUESTS,
    Right.RIGHT_TO_OPT_OUT: OTHER_REQUESTS,
    Right.RIGHT_TO_DELETE: DELETE_CHECKBOX_TEXT,
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (Step 2 offers one checkbox per request type; only the Delete label is recorded.)


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

        state_select = await tab.find(xpath="//select", raise_exc=False)
        if state_select:
            await state_select.execute_script(
                f"const w={SuperScraper.STATE.upper()!r};"
                "const o=[...this.options].find(x=>x.text.trim().toUpperCase()===w);"
                "if(o){const s=Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set;"
                "s.call(this,o.value);this.dispatchEvent(new Event('change',{bubbles:true}));}"
            )
        await asyncio.sleep(1)

        new_req = await tab.find(text="Make a new request", raise_exc=False)
        if new_req:
            await new_req.click()
            await asyncio.sleep(4)

        # Step 2: tick the request-type checkboxes — everything except the
        # "Delete personal information" option, which is only ticked when Right.RIGHT_TO_DELETE is requested
        for box in await tab.find(xpath="//input[@type='checkbox']", find_all=True, raise_exc=False) or []:
            if not await box.is_visible():
                continue
            text = await js_utils.js_eval(
                box,
                "const c=this.closest('label,li,div,tr');"
                "return c ? c.textContent.toLowerCase() : '';",
            ) or ""
            if DELETE_CHECKBOX_TEXT in text and Right.RIGHT_TO_DELETE not in rights:
                continue
            await js_utils.js_check(box)
            await asyncio.sleep(0.1)

        time.sleep(0.5)
        await SuperScraper.screenshot(tab, "dry_run_step2")
        cont = await tab.find(text="Continue", raise_exc=False)
        if cont:
            await cont.click()
            await asyncio.sleep(4)

        # Step 3: "Please tell us about yourself" identity form
        def _dob():
            raw = (SuperScraper.DATE_OF_BIRTH or "").strip()
            for sep in ("/", "-", "."):
                if sep in raw:
                    p = raw.split(sep)
                    if len(p) == 3 and len(p[2]) == 4:
                        return f"{int(p[1]):02d}/{int(p[0]):02d}/{p[2]}"  # MM/DD/YYYY
            return raw

        step3 = {
            "First Name": SuperScraper.FIRST_NAME,
            "Last Name": SuperScraper.LAST_NAME,
            "Date of Birth": _dob(),
            "Current Address": SuperScraper.ADDRESS,
            "ZIP Code": SuperScraper.ZIP_CODE,
            "City": SuperScraper.CITY,
            "Phone Number": SuperScraper.PHONE_NUMBER,
            "Email Address": SuperScraper.EMAIL,
            "Confirm Email Address": SuperScraper.EMAIL,
        }
        for label, value in step3.items():
            field = await tab.find(
                xpath=f"//label[normalize-space()={label!r} or starts-with(normalize-space(),{label!r})]"
                f"/following::input[1]",
                raise_exc=False,
            )
            if field and await field.is_visible():
                await field.type_text(value)
                await asyncio.sleep(0.2)

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, {
                label: (
                    f"//label[normalize-space()={label!r} or starts-with(normalize-space(),{label!r})]"
                    f"/following::input[1]"
                )
                for label in step3
            })

        time.sleep(0.5)
        await SuperScraper.screenshot(tab, "dry_run_step3")
        print(
            "Steps 1-3 filled (state, request types, identity details). The SSN field is "
            "left blank (optional; only a last-4 is on file) and the identity-VERIFICATION "
            "step that follows 'Save and Continue' — Experian is a credit bureau, so it is "
            "a knowledge-based / document check — must be completed manually."
        )


asyncio.run(main())
