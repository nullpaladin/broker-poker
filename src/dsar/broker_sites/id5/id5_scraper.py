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
#      DATA". Exercised only when REMOVE_INFORMATION.
#   3. Know section (section.know-request-section): ID5 ID (prefilled), MAID,
#      Email, an "I certify ..." #know-request-confirm checkbox, then buttons
#      "Know Categories of My Personal Data" / "Know Specific Pieces of My
#      Personal Data" / "Do Not Sell My Personal Information". Scraper fills the
#      email, ticks the certify box (covers Access + Do Not Sell).
#
# One pass per right; the section is filled and screenshotted, and the action
# button is only clicked when not DRY_RUN. No captcha observed.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://id5-sync.com/privacy/"


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
    await field.execute_script(
        "const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
        f"s.call(this,{value!r});"
        "this.dispatchEvent(new Event('input',{bubbles:true}));"
        "this.dispatchEvent(new Event('change',{bubbles:true}));"
    )
    await asyncio.sleep(0.3)


async def opt_out(tab):
    await tab.go_to(URL)
    await asyncio.sleep(7)
    await _click_checkbox_by_label(tab, ".optout-section", "with my id5 user id")
    await _click_checkbox_by_label(tab, ".optout-section", "with my email address")
    email = await tab.find(id="opt-out-email-input", raise_exc=False)
    if email:
        await email.execute_script(
            "const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
            f"s.call(this,{SuperScraper.EMAIL!r});"
            "this.dispatchEvent(new Event('input',{bubbles:true}));"
            "this.dispatchEvent(new Event('change',{bubbles:true}));"
        )
    time.sleep(0.5)
    await SuperScraper.screenshot(tab, "resources/screenshots/id5_dry_run_optout.png")
async def know(tab):
    await tab.go_to(URL)
    await asyncio.sleep(7)
    await _fill_email(tab, "know-request-section", SuperScraper.EMAIL)
    confirm = await tab.find(id="know-request-confirm", raise_exc=False)
    if confirm:
        await SuperScraper.js_check(confirm)
    time.sleep(0.5)
    await SuperScraper.screenshot(tab, "resources/screenshots/id5_dry_run_access.png")
    print(
        "Know section filled — click 'Know Specific Pieces of My Personal Data' (Access) "
        "and/or 'Do Not Sell My Personal Information' to submit."
    )


async def delete(tab):
    await tab.go_to(URL)
    await asyncio.sleep(7)
    await _fill_email(tab, "delete-request-section", SuperScraper.EMAIL)
    time.sleep(0.5)
    await SuperScraper.screenshot(tab, "resources/screenshots/id5_dry_run_delete.png")
    print("Delete section filled — click 'DELETE MY PERSONAL DATA' to submit.")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await opt_out(tab)
        await know(tab)
        if SuperScraper.wants("delete"):
            await delete(tab)

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: Opt-out + Know sections filled for <{SuperScraper.EMAIL}>"
                f"{' + Delete section' if SuperScraper.wants("delete") else ''}. "
                f"Each section has its own submit button (no shared submit)."
            )


asyncio.run(main())
