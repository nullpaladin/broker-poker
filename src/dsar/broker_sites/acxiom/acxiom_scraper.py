# acxiom.com — the public /optout/ page embeds the real form as an iframe
# (isapps.acxiom.com/optout/optout.aspx); navigating directly to that iframe
# src frame-busts back to the outer page (top-level anti-clickjacking
# redirect), so it must be driven in place as a `<iframe>` WebElement rather
# than visited directly. `iframe.find(...)` correctly resolves into the
# frame's own document (pydoll's IFrameContextResolver), but calling
# `.execute_script()` on the iframe WebElement itself runs in the OUTER
# document (`this` = the <iframe> tag, but `document` still means the
# parent's document) — for JS-driven selects (Identity, State) `.find()` the
# target element first from the iframe, then call `.execute_script()` on
# THAT element instead, which does run inside the frame.
#
# This is a legacy ASP.NET WebForms opt-out portal built around a "grid" of
# add-one-entry-at-a-time sections: fill Identity ("Me")/Name, click Add
# (AddName2), then fill one opt-out-segment-specific section and click its
# own Add button, then Submit. The "Select opt out segment" control looks
# like a multi-select chip widget but only ever keeps the most recently
# clicked chip (confirmed empirically — selecting a 2nd segment silently
# replaces the 1st), so this is actually single-select: one full add+submit
# pass per segment (Mail/Phone/Email), same one-submission-per-right pattern
# used elsewhere in this repo. Address entries additionally trigger a USPS
# standardization popup (SelectCorrected2 button) that must be accepted
# before the address is added to the list. Ends in a g-recaptcha (present in
# the DOM even though not visibly rendered until near submission) — requires
# a manual solve in live mode. No separate Access/Delete request type exists
# here — Acxiom's Right to Know/Right to Delete are handled elsewhere (a
# marketing-form email flow, not a self-service DSAR form), so this scraper
# only exercises the Opt-Out segments.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.acxiom.com/optout/"


async def _select_by_value(select_element, value):
    await select_element.execute_script(
        "for (var i=0;i<this.options.length;i++){"
        f"  if(this.options[i].value==={value!r}){{ this.selectedIndex=i; }}"
        "}"
        "this.dispatchEvent(new Event('change', {bubbles:true}));"
    )


async def _add_name(iframe):
    who = await iframe.find(id="Identity")
    await _select_by_value(who, "Submitter")
    await asyncio.sleep(0.5)

    first = await iframe.find(id="FirstName")
    await first.click()
    await first.type_text(SuperScraper.FIRST_NAME)
    last = await iframe.find(id="LastName")
    await last.click()
    await last.type_text(SuperScraper.LAST_NAME)
    await asyncio.sleep(0.5)

    add_name_btn = await iframe.find(id="AddName2")
    await add_name_btn.click()
    await asyncio.sleep(1.5)


async def _fill_mail(iframe):
    street = await iframe.find(id="Street1")
    await street.click()
    await street.type_text(SuperScraper.ADDRESS)
    city = await iframe.find(id="City")
    await city.click()
    await city.type_text(SuperScraper.CITY)
    state = await iframe.find(id="State")
    state_abbr = SuperScraper.STATE_ABBREVIATED
    await _select_by_value(state, state_abbr)
    zip_field = await iframe.find(id="Zip")
    await zip_field.click()
    await zip_field.type_text(SuperScraper.ZIP_CODE)
    await asyncio.sleep(0.5)

    add_btn = await iframe.find(id="AddAddress2")
    await add_btn.click()
    await asyncio.sleep(1.5)

    select_corrected = await iframe.find(id="SelectCorrected2", raise_exc=False)
    if select_corrected:
        await select_corrected.click()
        await asyncio.sleep(1)


async def _fill_phone(iframe):
    digits = "".join(c for c in SuperScraper.PHONE_NUMBER if c.isdigit())
    area_code, rest = digits[:3], digits[3:]

    area_field = await iframe.find(id="AreaCode")
    await area_field.click()
    await area_field.type_text(area_code)
    phone_field = await iframe.find(id="PhoneNumber")
    await phone_field.click()
    await phone_field.type_text(rest)
    await asyncio.sleep(0.5)

    add_btn = await iframe.find(id="AddPhone2")
    await add_btn.click()
    await asyncio.sleep(1.5)


async def _fill_email(iframe):
    email_field = await iframe.find(id="Email")
    await email_field.click()
    await email_field.type_text(SuperScraper.EMAIL)
    await asyncio.sleep(0.5)

    add_btn = await iframe.find(id="AddEmail2")
    await add_btn.click()
    await asyncio.sleep(1.5)


SEGMENTS = {
    "mail": ("Mailing Addresses", _fill_mail),
    "phone": ("Phone Numbers", _fill_phone),
    "email": ("Email Addresses", _fill_email),
}


async def submit_segment(tab, segment_key, super_scraper):
    label, fill_fn = SEGMENTS[segment_key]

    await tab.go_to(URL)
    await asyncio.sleep(4)

    ok_btn = await tab.find(text="OK", raise_exc=False)
    if ok_btn:
        await ok_btn.click()
        await asyncio.sleep(1)

    iframe = await tab.find(id="frameresize", raise_exc=False)
    if not iframe:
        print(f"{super_scraper.OOPS} opt-out iframe not found for {segment_key}")
        return

    segment_dropdown = await iframe.find(text="Select opt out segment", raise_exc=False)
    if not segment_dropdown:
        print(f"{super_scraper.OOPS} segment dropdown not found for {segment_key}")
        return
    await segment_dropdown.click()
    await asyncio.sleep(1.5)
    segment_option = await iframe.find(text=label, raise_exc=False)
    if not segment_option:
        print(f"{super_scraper.OOPS} segment option '{label}' not found")
        return
    await segment_option.click()
    await asyncio.sleep(1)

    await _add_name(iframe)
    await fill_fn(iframe)

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit {segment_key} opt-out for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/acxiom_dry_run_{segment_key}.png")
        return

    print(f"\n{segment_key} opt-out filled. Solve the reCAPTCHA, then press Enter to submit...")
    input()

    submit_btn = await iframe.find(id="SubmitButton2")
    await submit_btn.click()
    await asyncio.sleep(2)
    print(f"Submitted {segment_key} opt-out for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for segment_key in SEGMENTS:
            await submit_segment(tab, segment_key, super_scraper)


asyncio.run(main())
