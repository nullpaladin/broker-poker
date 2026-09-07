# seekout.com — the /privacy/choices/ page embeds a HubSpot form via a
# share-link iframe (share-na2.hsforms.com/2vQIxZUeERGOPFcRto1AFgw). Unlike a
# src-less hbspt.forms.create embed, the share link is a real navigable URL, so
# this drives it directly.
#
# Fields (HubSpot property names are stable; the numeric element ids are not, so
# everything is targeted by name / label text):
#   0-1/privacyindividualoragent  radio -> "I am the individual"
#   0-1/firstname / 0-1/lastname (required), 0-1/email
#   0-1/hs_linkedin_url  "LinkedIn Profile" (required) -> LINKEDIN_URL
#   Country  combobox -> United States
#   State/Region Code  text -> the 2-letter state abbreviation
#   0-1/privacy_choice  checkbox group (multi-select, one combined submission):
#       "Request A Copy of My Personal Information" (Access) + "Do Not Sell or
#       Share My Information" unconditionally; "Delete My Personal Information"
#       gated on REMOVE_INFORMATION; Correction / "Limit Use of Sensitive ..."
#       skipped.
# reCAPTCHA Enterprise gates submit — filled to that point.
# **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://40ros1.share-na2.hsforms.com/2vQIxZUeERGOPFcRto1AFgw"

CHOICES = [
    "Request A Copy of My Personal Information",
    "Do Not Sell or Share My Information",
]
DELETE_CHOICE = "Delete My Personal Information"


async def _type_by_name(tab, super_scraper, name, value):
    if not value:
        return
    el = await tab.find(xpath=f"//input[@name={name!r}]", raise_exc=False)
    if el:
        await el.type_text(value)
        await asyncio.sleep(0.2)
    else:
        print(f"{super_scraper.OOPS} field name={name!r} not found")


async def _click_label(tab, super_scraper, text):
    for xp in (
        f"//label[.//text()[contains(normalize-space(), {text!r})]]",
        f"//*[normalize-space()={text!r}]/ancestor::label[1]",
        f"//span[contains(normalize-space(), {text!r})]",
    ):
        el = await tab.find(xpath=xp, raise_exc=False)
        if el:
            await el.click()
            await asyncio.sleep(0.2)
            return True
    print(f"{super_scraper.OOPS} option {text!r} not found")
    return False


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    state_abbr = SuperScraper.STATE_ABBREVIATED
    choices = list(CHOICES)
    if SuperScraper.REMOVE_INFORMATION:
        choices.append(DELETE_CHOICE)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(8)

        await _click_label(tab, super_scraper, "I am the individual")

        await _type_by_name(tab, super_scraper, "0-1/firstname", SuperScraper.FIRST_NAME)
        await _type_by_name(tab, super_scraper, "0-1/lastname", SuperScraper.LAST_NAME)
        await _type_by_name(tab, super_scraper, "0-1/email", SuperScraper.EMAIL)
        await _type_by_name(tab, super_scraper, "0-1/hs_linkedin_url", SuperScraper.LINKEDIN_URL)

        # Country and State/Region Code are both HubSpot comboboxes (type, then
        # click the matching <li>/role=option).
        async def _combo(label_contains, typed, want_options):
            field = await tab.find(
                xpath=(
                    f"//label[contains(normalize-space(), {label_contains!r})]"
                    "/following::input[contains(@id,'-input')][1]"
                ),
                raise_exc=False,
            )
            if not field:
                print(f"{super_scraper.OOPS} combobox for {label_contains!r} not found")
                return
            await field.click()
            await asyncio.sleep(0.4)
            await tab.keyboard.type_text(typed)
            await asyncio.sleep(1.3)
            for want in want_options:
                opt = await tab.find(
                    xpath=f"//*[(@role='option' or self::li) and normalize-space()={want!r}]",
                    raise_exc=False,
                )
                if opt:
                    await opt.click()
                    await asyncio.sleep(0.4)
                    return
            print(f"{super_scraper.OOPS} no option matched for {label_contains!r} ({typed!r})")

        await _combo("Country", "United States", ["United States of America", "United States"])

        # "State/Region Code" takes the 2-letter code as free text.
        state_field = await tab.find(
            xpath=(
                "//label[contains(normalize-space(), 'State/Region Code')]"
                "/following::input[contains(@id,'-input')][1]"
            ),
            raise_exc=False,
        )
        if state_field:
            await state_field.click()
            await asyncio.sleep(0.3)
            await tab.keyboard.type_text(state_abbr)
            await asyncio.sleep(0.4)
            opt = await tab.find(
                xpath=f"//*[(@role='option' or self::li) and normalize-space()={state_abbr!r}]",
                raise_exc=False,
            )
            if opt:
                await opt.click()
        else:
            print(f"{super_scraper.OOPS} State/Region Code field not found")

        for choice in choices:
            await _click_label(tab, super_scraper, choice)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/seekout_dry_run.png", beyond_viewport=True)
        print(f"{choices} filled but NOT submitted — solve the reCAPTCHA manually, then Submit.")


asyncio.run(main())
