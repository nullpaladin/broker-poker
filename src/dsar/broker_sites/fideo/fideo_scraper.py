# fideo.ai — single-select radio wizard (one right per pass): Access,
# Correct, Do Not Sell, Limit Sharing of Sensitive Data unconditionally;
# Delete gated on REMOVE_INFORMATION. Each right's radio is a visually-hidden
# input with a same-level (not ancestor) <label for="..."> — click the label
# by xpath, not the input. Flow per right: pick radio -> Continue -> country
# (defaults to United States) -> Continue -> choose verification method
# ("Use My Email") -> type email -> "Send Me A Code".
#
# Every right requires OTP email/phone verification before any name/address
# collection happens — there is no unverified path. Clicking "Send Me A
# Code" triggers a real email send, so this scraper stops just before that
# button (having already typed the email in) regardless of DRY_RUN, and
# hands off to the user to click Send, check their inbox, enter the code,
# and complete whatever form follows — not observed/automatable past this
# point.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://app.fideo.ai/your-privacy-choices"

RIGHTS = [
    ("radio-access-data", "access"),
    ("radio-correct-data", "correct"),
    ("radio-dnsell-data", "opt_out"),
    ("radio-limit-data", "limit_sensitive"),
]
DELETE_RIGHT = ("radio-delete-data", "delete")


async def _click_continue(tab):
    return await tab.execute_script(
        "var btns = Array.from(document.querySelectorAll('button')); "
        "var b = btns.find(x=>x.textContent.trim().toLowerCase()==='continue'); "
        "if(b){ b.click(); return true;} return false;"
    )


async def submit_request(tab, radio_id, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    radio_label = await tab.find(xpath=f"//label[@for='{radio_id}']", raise_exc=False)
    if not radio_label:
        print(f"{super_scraper.OOPS} Radio label for '{radio_id}' not found")
        return
    await radio_label.click()
    await asyncio.sleep(1)

    await _click_continue(tab)  # confirm right selection
    await asyncio.sleep(2)
    await _click_continue(tab)  # confirm country (defaults to United States)
    await asyncio.sleep(2)

    use_email = await tab.execute_script(
        "var btns = Array.from(document.querySelectorAll('button')); "
        "var b = btns.find(x=>x.textContent.trim().toLowerCase().includes('use my email')); "
        "if(b){ b.click(); return true;} return false;"
    )
    if not use_email:
        print(f"{super_scraper.OOPS} 'Use My Email' button not found for '{label}'")
        return
    await asyncio.sleep(1)

    email_field = await tab.find(xpath="//input[@placeholder='Enter Your Email Address']", raise_exc=False)
    if email_field:
        await email_field.type_text(SuperScraper.EMAIL)

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/fideo_dry_run_{label}.png")
    print(
        f"\n'{label}' request ready but NOT sent — click 'Send Me A Code' yourself, "
        "check your email for the verification code, enter it, and complete whatever "
        "form follows manually. This step sends a real email regardless of DRY_RUN, "
        "so it is never done automatically."
    )


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
        for radio_id, label in rights:
            await submit_request(tab, radio_id, label, super_scraper)


asyncio.run(main())
