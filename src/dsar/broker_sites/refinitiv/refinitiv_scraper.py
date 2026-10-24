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
# exercise" field states which right(s) (SuperScraper.request_statement over the
# rights selected by rights_to_exercise), same pattern as groundtruth.com/pulsepoint.com
# elsewhere in this repo. The whole run is ONE form fill covering all selected rights.
# Optional Middle Name/Personal Email/Additional
# Info fields left blank. captchaCode is a BotDetect image CAPTCHA —
# **CAPTCHA solution required**.
#
# Page elements:
#   stateDSARElement            "State" vt-autocomplete (optional)
#   role=option grid            "I am" subject type -> SUBJECT_TYPE; "Does your request relate to TORA?" -> "No"
#   firstNameDSARElement        First name
#   lastNameDSARElement         Last name
#   emailDSARElement            Email
#   cityDSARElement             City
#   requestDetailsDSARElement   "Please provide specific information on the data subject rights that you wish to exercise"
#   captchaCode                 BotDetect image CAPTCHA (manual entry)
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://privacyportal-de.onetrust.com/webform/5f7a2da0-bed0-45e8-ac2c-c1f297e2efdc/4ae30ef5-8107-4353-a0b5-1bf34dd647f6"

# The form has no right picker; the chosen rights are described in the free-text field.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "access",
    Right.RIGHT_TO_DELETE: "delete",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (The form has no rights chooser: the rights are stated in the free-text field.)

FIELD_XPATHS = {
    "First name": "//*[@id='firstNameDSARElement']",
    "Last name": "//*[@id='lastNameDSARElement']",
    "Email": "//*[@id='emailDSARElement']",
    "City": "//*[@id='cityDSARElement']",
    "Request details": "//*[@id='requestDetailsDSARElement']",
}

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
    super_scraper = SuperScraper()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    options = SuperScraper.build_chromium_options()

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

        request_text = SuperScraper.request_statement(rights, broker="LSEG")
        details_field = await tab.find(id="requestDetailsDSARElement", raise_exc=False)
        if details_field:
            await details_field.type_text(request_text)

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run_" + "_".join(r.value for r in rights))
        print(
            "\nRequest filled but NOT submitted — a BotDetect image CAPTCHA requires "
            "manual entry before submitting."
        )


asyncio.run(main())
