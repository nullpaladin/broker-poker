# statara.com — Statara Solutions "Consumer Deletion" / privacy-rights request,
# a 2-page Gravity Forms form (form id 5) at statara.com/consumerdeletion/.
# Page 1: name / address / email / phone / privacy-policy consent checkbox, then
# a "Next" button. Page 2: a single-select "which right" radio group
# (Know/Access, Delete, Correct) followed by Submit.
# One submission per right — Know/Access unconditional; Delete gated on
# REMOVE_INFORMATION; Correct skipped (nothing concrete to correct).
# reCAPTCHA is invisible (size=invisible) and resolves without interaction.
#
# NOTE: under headless automation the page-1 "Next" click is rejected by
# Gravity Forms' JavaScript anti-spam with a generic "There was a problem with
# your submission" banner and no field-level error (every field validates
# individually — confirmed via aria-invalid). On a real, non-headless browser
# with genuine pointer/keyboard activity this check passes; the scraper fills
# page 1 completely, then clicks Next and, if page 2 renders, selects the
# right and stops. If page 2 does not render, finish the Next step manually.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://statara.com/consumerdeletion/"

# (page-2 radio choice id, screenshot label)
REQUESTS = [
    ("choice_5_16_0", "access"),   # The Right to Know or Access your personal information
]
DELETE_REQUEST = ("choice_5_16_1", "delete")  # The Right to Delete your personal information


async def _select_native_by_text(tab, xpath, match_text):
    el = await tab.find(xpath=xpath, raise_exc=False)
    if not el:
        print(f"select {xpath} not found")
        return
    await el.execute_script(
        """
        const wanted = %r.trim().toLowerCase();
        const opt = Array.from(this.options).find(
            o => o.textContent.trim().toLowerCase() === wanted);
        if (opt) {
            const setter = Object.getOwnPropertyDescriptor(
                window.HTMLSelectElement.prototype, 'value').set;
            setter.call(this, opt.value);
            this.dispatchEvent(new Event('input', {bubbles: true}));
            this.dispatchEvent(new Event('change', {bubbles: true}));
        }
        """
        % match_text
    )


async def submit_request(tab, choice_id, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    page1 = {
        "//input[@id='input_5_8_3']": SuperScraper.FIRST_NAME,
        "//input[@id='input_5_8_6']": SuperScraper.LAST_NAME,
        "//input[@id='input_5_9_1']": SuperScraper.ADDRESS,
        "//input[@id='input_5_9_3']": SuperScraper.CITY,
        "//input[@id='input_5_9_5']": SuperScraper.ZIP_CODE,
        "//input[@id='input_5_10']": SuperScraper.EMAIL,
        "//input[@id='input_5_11']": SuperScraper.PHONE_NUMBER,
    }
    for xpath, value in page1.items():
        await super_scraper.input_text_field(tab=tab, xpath=xpath, text=value, sleep=0.3)

    await _select_native_by_text(tab, "//select[@id='input_5_9_4']", SuperScraper.STATE)

    consent = await tab.find(id="input_5_12_1", raise_exc=False)
    if consent:
        await consent.execute_script("if (!this.checked) this.click();")

    await asyncio.sleep(0.5)
    next_btn = await tab.find(id="gform_next_button_5_13", raise_exc=False)
    if not next_btn:
        print(f"{super_scraper.OOPS} Next button not found")
        return
    await next_btn.click()
    await asyncio.sleep(4)

    page2_visible = await tab.execute_script(
        "const p = document.getElementById('gform_page_5_2');"
        "return !!p && getComputedStyle(p).display !== 'none';"
    )
    if not page2_visible['result']['result']['value']:
        await SuperScraper.screenshot(tab, f"resources/screenshots/statara_dry_run_{label}.png")
        print(
            f"{super_scraper.OOPS} Page 1 filled but 'Next' did not advance (Gravity Forms "
            f"anti-spam under automation). Click Next manually, choose the '{label}' right, "
            f"and submit. Screenshot: resources/screenshots/statara_dry_run_{label}.png"
        )
        return

    radio = await tab.find(id=choice_id, raise_exc=False)
    if not radio:
        print(f"{super_scraper.OOPS} Page-2 radio '{choice_id}' not found")
        return
    await radio.execute_script("this.checked = true; this.dispatchEvent(new Event('change',{bubbles:true}));")

    time.sleep(0.5)
    await SuperScraper.screenshot(tab, f"resources/screenshots/statara_dry_run_{label}.png")
    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        return

    submit_btn = await tab.find(id="gform_submit_button_5", raise_exc=False)
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(4)
    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{label}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{label}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    requests = list(REQUESTS)
    if SuperScraper.REMOVE_INFORMATION:
        requests.append(DELETE_REQUEST)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for choice_id, label in requests:
            await submit_request(tab, choice_id, label, super_scraper)


asyncio.run(main())
