# id5.io — ID5 Privacy Preference Center at https://id5-sync.com/privacy/
# (linked from id5.io). A Vue single-page app with three independent, cookie-
# identity-based sections, each with its own submit button (no shared submit):
#
#   1. Opt-out section (#optoutRestButton): three "I would like to Opt Out"
#      checkboxes — "with my ID5 User ID", "with my Email Address" (reveals
#      #opt-out-email-input), "with my MAID" (reveals #opt-out-maid-input +
#      #opt-out-maid-type). Scraper ticks the User-ID and Email boxes and fills
#      the email; MAID left off (only a placeholder ADVERTISING_ID on file).
#   2. Delete section (section.delete-request-section): ID5 ID (prefilled from
#      the browser cookie), MAID, Email (required). Button "DELETE MY PERSONAL
#      DATA".
#   3. Know section (section.know-request-section): ID5 ID (prefilled), MAID,
#      Email, an "I certify ..." #know-request-confirm checkbox, then buttons
#      "Know Categories of My Personal Data" / "Know Specific Pieces of My
#      Personal Data" / "Do Not Sell My Personal Information". Scraper fills the
#      email, ticks the certify box (covers Access + Do Not Sell).
#
# One pass per right (decided only by SuperScraper.rights_to_exercise); the section
# is filled and screenshotted, and the action button is left for the user to click.
# No captcha observed. Rights: OPT_OUT -> opt-out section; ACCESS -> Know section
# (also hosts "Do Not Sell My Personal Information"); DELETE -> delete section.
#
# Page elements:
#   .optout-section                       Opt-out section
#     checkbox "I would like to Opt Out with my ID5 User ID"
#     checkbox "I would like to Opt Out with my Email Address"
#     #opt-out-email-input                Email (revealed by the email checkbox)
#   section.know-request-section          Know section
#     input[type=email]                   Email
#     #know-request-confirm               "I certify ..." checkbox
#   section.delete-request-section        Delete section
#     input[type=email]                   Email
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper
from src.dsar import js_utils

URL = "https://id5-sync.com/privacy/"

# Right -> which section of the page handles it.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "know",
    Right.RIGHT_TO_OPT_OUT: "optout",
    Right.RIGHT_TO_DELETE: "delete",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def _click_checkbox_by_label(tab, section_selector, label_text):
    await tab.execute_script(
        f"const sec=document.querySelector({section_selector!r});"
        "if(sec){for(const l of sec.querySelectorAll('label')){"
        f"  if(l.textContent.trim().toLowerCase().includes({label_text.lower()!r})){{"
        "    const cb=l.querySelector('input[type=checkbox]')||"
        "      (l.previousElementSibling && l.previousElementSibling.matches('input[type=checkbox]') ? l.previousElementSibling : null);"
        "    if(cb && !cb.checked){cb.click();}"
        "    break;"
        "  }"
        "}}"
    )
    await asyncio.sleep(0.4)


async def _fill_email(tab, section_selector, value):
    field = await tab.find(xpath=f"//section[contains(@class,{section_selector!r})]//input[@type='email']", raise_exc=False)
    if not field:
        return
    await js_utils.js_set_value(field, value)
    await asyncio.sleep(0.3)


async def opt_out(tab):
    await tab.go_to(URL)
    await asyncio.sleep(7)
    await _click_checkbox_by_label(tab, ".optout-section", "with my id5 user id")
    await _click_checkbox_by_label(tab, ".optout-section", "with my email address")
    email = await tab.find(id="opt-out-email-input", raise_exc=False)
    if email:
        await js_utils.js_set_value(email, SuperScraper.EMAIL)
    time.sleep(0.5)
    await SuperScraper.screenshot(tab, "dry_run_opt_out")
    print("Opt-out section filled — click the opt-out button to submit.")


async def know(tab):
    await tab.go_to(URL)
    await asyncio.sleep(7)
    await _fill_email(tab, "know-request-section", SuperScraper.EMAIL)
    confirm = await tab.find(id="know-request-confirm", raise_exc=False)
    if confirm:
        await js_utils.js_check(confirm)
    time.sleep(0.5)
    await SuperScraper.screenshot(tab, "dry_run_access")
    print(
        "Know section filled — click 'Know Specific Pieces of My Personal Data' (Access) "
        "and/or 'Do Not Sell My Personal Information' to submit."
    )


async def delete(tab):
    await tab.go_to(URL)
    await asyncio.sleep(7)
    await _fill_email(tab, "delete-request-section", SuperScraper.EMAIL)
    time.sleep(0.5)
    await SuperScraper.screenshot(tab, "dry_run_delete")
    print("Delete section filled — click 'DELETE MY PERSONAL DATA' to submit.")


SECTIONS = {"optout": opt_out, "know": know, "delete": delete}


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await SECTIONS[RIGHT_MAP[right]](tab)

        if SuperScraper.DRY_RUN:
            names = ", ".join(r.name for r in rights)
            print(
                f"DRY RUN: sections filled for <{SuperScraper.EMAIL}> ({names}). "
                f"Each section has its own submit button (no shared submit)."
            )


asyncio.run(main())
