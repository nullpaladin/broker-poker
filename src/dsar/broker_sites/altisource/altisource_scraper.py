# altisource.com — /contact-us/ is a single Gravity Forms contact form whose
# visible fields change based on a "Select One" reason dropdown
# (id=input_1_13). Choosing "Privacy Data (Access/Delete)" reveals First/Last
# Name, Email, Phone, Company, a required "Area of Interest" checkbox group,
# and a free-text Message — there's no dedicated Access vs Delete selector,
# so the specific ask (Access, Do Not Sell, and optionally Delete) is stated
# in the message body. "Area of Interest" is a leftover from the generic
# contact-form template (Servicer/Origination/Technology/Real Estate
# Investors business lines) — none of it is relevant to a privacy request,
# but the group is required, so the first checkbox is ticked purely to
# satisfy validation. No captcha observed.
#
# NOTE: the PHONE field has a JS input mask ("(___) ___-____") that
# corrupts simulated keystrokes typed via type_text() — even one character
# at a time with delays, only the last few digits ever land, the rest stay
# blank underscores. Setting the value via the native input-value setter +
# input/change/blur event dispatch instead lets the mask library reformat
# the whole string correctly in one pass.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.altisource.com/contact-us/"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        reject = await tab.find(text="Reject All", raise_exc=False)
        if reject:
            await reject.click()
            await asyncio.sleep(1)

        category_select = await tab.find(id="input_1_13", raise_exc=False)
        if not category_select:
            print(f"{super_scraper.OOPS} category dropdown not found")
            return
        await category_select.execute_script(
            "for (var i=0;i<this.options.length;i++){"
            "  if(this.options[i].value==='Privacy Data (Access/Delete)'){ this.selectedIndex=i; }"
            "}"
            "this.dispatchEvent(new Event('change', {bubbles:true}));"
        )
        await asyncio.sleep(2)

        first = await tab.find(id="input_1_14_3", raise_exc=False)
        last = await tab.find(id="input_1_14_6", raise_exc=False)
        email = await tab.find(id="input_1_4", raise_exc=False)
        phone = await tab.find(id="input_1_5", raise_exc=False)
        company = await tab.find(id="input_1_41", raise_exc=False)
        message = await tab.find(id="input_1_7", raise_exc=False)

        if first:
            await first.click()
            await first.type_text(SuperScraper.FIRST_NAME)
        if last:
            await last.click()
            await last.type_text(SuperScraper.LAST_NAME)
        if email:
            await email.click()
            await email.type_text(SuperScraper.EMAIL)
        if phone:
            digits = "".join(c for c in SuperScraper.PHONE_NUMBER if c.isdigit())
            await phone.execute_script(
                "var proto = Object.getPrototypeOf(this);"
                "var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;"
                f"setter.call(this, {digits!r});"
                "this.dispatchEvent(new Event('input', {bubbles:true}));"
                "this.dispatchEvent(new Event('change', {bubbles:true}));"
                "this.dispatchEvent(new Event('blur', {bubbles:true}));"
            )
        if company:
            await company.click()
            await company.type_text(SuperScraper.COMPANY_NAME or "N/A")

        area_of_interest = await tab.find(id="choice_1_18_1", raise_exc=False)
        if area_of_interest:
            await area_of_interest.click()

        if SuperScraper.REMOVE_INFORMATION:
            request_text = (
                f"I am {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}. I am requesting access to "
                "the personal information you have collected about me, that you do not sell/share it, "
                "and that you delete my personal information."
            )
        else:
            request_text = (
                f"I am {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}. I am requesting access to "
                "the personal information you have collected about me, and that you do not sell/share it."
            )
        if message:
            await message.click()
            await message.type_text(request_text)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit removal request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "resources/screenshots/altisource_dry_run.png")
            return

        submit_btn = await tab.find(id="gform_submit_button_1", raise_exc=False)
        if submit_btn:
            await submit_btn.click()
            await asyncio.sleep(2)
            print(f"Submitted removal request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        else:
            print(f"{super_scraper.OOPS} SEND button not found")


asyncio.run(main())
