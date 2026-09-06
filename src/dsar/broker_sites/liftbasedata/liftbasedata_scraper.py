# liftbasedata.com — request-to-know/liftbase/. Page is titled "Opt-Out
# Request" but that's really the umbrella for the whole form — the actual
# rights are exercised via independent Yes/No <select> toggles further
# down (a Gravity Forms form, `input_N` naming), NOT single-select radios:
# "Delete all the personal data..." (Delete, gated on REMOVE_INFORMATION),
# "Send a summary [of] the data categories..." and "Send a summary of
# where the data... has been shared" (together = Access/Right-to-Know —
# both set Yes unconditionally), "Correct / update my data..." (skipped,
# auxiliary). Because these are independent toggles on ONE form rather than
# a single-select request-type picker, this is a single submission with
# every desired toggle set, not one submission per right.
#
# "Are you acting as an agency on behalf of a consumer?" must be answered
# "No" first — the entire Consumer Information / Mailing Address / rights-
# toggle section only renders in the DOM after that. Marital Status is a
# required select with no "prefer not to answer" option (Single/Married
# only) — "Single" is used as the arbitrary required pick. DATE_OF_BIRTH
# (DD/MM/YYYY per this repo's .env convention) is split into separate
# MM/DD/YYYY number inputs. Both Cloudflare Turnstile and reCAPTCHA v2 are
# present — **CAPTCHA solution required**; the form is filled completely
# and left there regardless.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.liftbasedata.com/request-to-know/liftbase/"


def _select_by_text(text):
    return (
        "for (var i=0;i<this.options.length;i++){"
        f"  if(this.options[i].text==={text!r}){{ this.selectedIndex=i; }}"
        "}"
        "this.dispatchEvent(new Event('change', {bubbles:true}));"
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        agency_select = await tab.find(id="input_1_16", raise_exc=False)
        if not agency_select:
            agency_select = await tab.find(xpath="//select", raise_exc=False)
        if agency_select:
            await agency_select.execute_script(_select_by_text("No"))
        await asyncio.sleep(2)

        first_field = await tab.find(id="input_1_1_3", raise_exc=False)
        if first_field:
            await first_field.type_text(SuperScraper.FIRST_NAME)
        last_field = await tab.find(id="input_1_1_6", raise_exc=False)
        if last_field:
            await last_field.type_text(SuperScraper.LAST_NAME)

        try:
            day, month, year = SuperScraper.DATE_OF_BIRTH.split("/")
        except (ValueError, AttributeError):
            month, day, year = "01", "01", "1980"
        dob_fields = {"input_1_3_1": month, "input_1_3_2": day, "input_1_3_3": year}
        for field_id, value in dob_fields.items():
            field = await tab.find(id=field_id, raise_exc=False)
            if field:
                await field.type_text(value)

        marital_select = await tab.find(id="input_1_28", raise_exc=False)
        if marital_select:
            await marital_select.execute_script(_select_by_text("Single"))

        email_field = await tab.find(id="input_1_4", raise_exc=False)
        if email_field:
            await email_field.type_text(SuperScraper.EMAIL)
        confirm_email_field = await tab.find(id="input_1_4_2", raise_exc=False)
        if confirm_email_field:
            await confirm_email_field.type_text(SuperScraper.EMAIL)

        address_fields = {
            "input_1_9_1": SuperScraper.ADDRESS,
            "input_1_9_2": SuperScraper.ADDRESS_LINE_TWO,
            "input_1_9_3": SuperScraper.CITY,
            "input_1_9_5": SuperScraper.ZIP_CODE,
        }
        for field_id, value in address_fields.items():
            if not value:
                continue
            field = await tab.find(id=field_id, raise_exc=False)
            if field:
                await field.type_text(value)

        state_select = await tab.find(id="input_1_9_4", raise_exc=False)
        if state_select:
            await state_select.execute_script(_select_by_text(SuperScraper.STATE))

        delete_select = await tab.find(id="input_1_26", raise_exc=False)
        if delete_select:
            await delete_select.execute_script(
                _select_by_text("Yes" if SuperScraper.REMOVE_INFORMATION else "No")
            )

        categories_select = await tab.find(id="input_1_24", raise_exc=False)
        if categories_select:
            await categories_select.execute_script(_select_by_text("Yes"))

        sharing_select = await tab.find(id="input_1_25", raise_exc=False)
        if sharing_select:
            await sharing_select.execute_script(_select_by_text("Yes"))

        correct_select = await tab.find(id="input_1_27", raise_exc=False)
        if correct_select:
            await correct_select.execute_script(_select_by_text("No"))

        await asyncio.sleep(1)
        await tab.take_screenshot(path="resources/screenshots/liftbasedata_dry_run.png")
        print("Screenshot saved to resources/screenshots/liftbasedata_dry_run.png")
        print(
            "\nForm filled but NOT submitted — both Cloudflare Turnstile and reCAPTCHA v2 "
            "are present and require a manual solve before submitting."
        )


asyncio.run(main())
