# refinitiv.com (LSEG — London Stock Exchange Group) — custom OneTrust
# Angular portal. This is LSEG's GENERAL data subject rights form; the
# page's own copy says NOT to use it for a CCPA-specific (California) or
# POPIA-specific (South Africa) request, or a World-Check-only request —
# those have their own separate linked forms not covered here. Country
# defaults to United States already; State is optional (vt-autocomplete,
# only filled if present). "I am" (subjectTypesDSARElement) is a
# role="option" grid with no generic-consumer-of-a-data-broker option —
# "a person whose personal information is part of the content of our
# products and services" is used as the closest fit (LSEG's data products
# include screening/reference data about people who are not customers).
# "Does your request relate to TORA?" (a specific trading product,
# formField23DSARElement) is unrelated — answered "No". No discrete
# right-type picker at all — a required free-text "Please provide
# specific information on the data subject rights that you wish to
# exercise" field states which right(s) (deletion only mentioned when
# REMOVE_INFORMATION is set), same pattern as groundtruth.com/pulsepoint.com
# elsewhere in this repo. Optional Middle Name/Personal Email/Additional
# Info fields left blank. captchaCode is a BotDetect image CAPTCHA —
# **CAPTCHA solution required**.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://privacyportal-de.onetrust.com/webform/5f7a2da0-bed0-45e8-ac2c-c1f297e2efdc/4ae30ef5-8107-4353-a0b5-1bf34dd647f6"

SUBJECT_TYPE = "a person whose personal information is part of the content of our products and services"


async def _select_option(tab, option_text, super_scraper, description):
    option = await tab.find(xpath=f"//*[@role='option' and normalize-space()='{option_text}']", raise_exc=False)
    if option:
        await option.click()
        await asyncio.sleep(0.7)
    else:
        print(f"{super_scraper.OOPS} {description} option '{option_text}' not found")


async def _autocomplete_select(tab, field_id, text, super_scraper, description):
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        return
    await field.click()
    await asyncio.sleep(0.3)
    await tab.keyboard.type_text(text)
    await asyncio.sleep(1.2)
    option = await tab.find(xpath=f"//*[@role='option' and normalize-space()='{text}']", raise_exc=False)
    if option:
        await option.click()
        await asyncio.sleep(0.7)
    else:
        print(f"{super_scraper.OOPS} {description} option '{text}' not found")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        await _autocomplete_select(tab, "stateDSARElement", SuperScraper.STATE, super_scraper, "state")
        await _select_option(tab, SUBJECT_TYPE, super_scraper, "'I am'")
        await _select_option(tab, "No", super_scraper, "TORA")

        first_field = await tab.find(id="firstNameDSARElement", raise_exc=False)
        if first_field:
            await first_field.type_text(SuperScraper.FIRST_NAME)
        last_field = await tab.find(id="lastNameDSARElement", raise_exc=False)
        if last_field:
            await last_field.type_text(SuperScraper.LAST_NAME)
        email_field = await tab.find(id="emailDSARElement", raise_exc=False)
        if email_field:
            await email_field.type_text(SuperScraper.EMAIL)
        city_field = await tab.find(id="cityDSARElement", raise_exc=False)
        if city_field:
            await city_field.type_text(SuperScraper.CITY)

        if SuperScraper.wants("delete"):
            request_text = "I am requesting access to and deletion of my personal information."
        else:
            request_text = "I am requesting access to my personal information."
        details_field = await tab.find(id="requestDetailsDSARElement", raise_exc=False)
        if details_field:
            await details_field.type_text(request_text)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/refinitiv_dry_run.png")
        print(
            "\nRequest filled but NOT submitted — a BotDetect image CAPTCHA requires "
            "manual entry before submitting."
        )


asyncio.run(main())
