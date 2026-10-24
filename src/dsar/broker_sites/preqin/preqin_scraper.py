# preqin.com — preqin.com/policies/data-rights only embeds a frame-bustable
# iframe; navigate directly to the underlying portal:
# https://portals.dporganizer.com/cbf39a0c-c047-4a7b-814d-c9d45754b4af (a
# DPOrganizer/DataGuard-hosted form, new platform for this repo — Preqin is
# a BlackRock company, portal branded accordingly).
#
# The portal's own banner states it is "dedicated to residents of
# California and Texas. For any other jurisdiction, please email us on
# GroupPrivacy@BlackRock.com" — the "US State" field is a react-select with
# ONLY those two options, no free-text/other-state entry. The scraper selects the
# user's own STATE (California or Texas) and bails for any other state
# (SERVES_NO_LAW_STATES = False covers states without a law; other law states are
# checked in main()) rather than claiming a residency the user does not have.
#
# "Type of request" is a GENUINELY multi-select react-select (Select
# all/Deselect all buttons, chips) — unlike most sites in this repo, all
# applicable rights are checked in ONE combined submission rather than one
# submission per right. Options: Erasure, Data portability, Correction,
# Know or Access, Opt-out from Cross-Context Behavioral Advertising or
# Targeted Advertising, Opt-out from Sales of Personal Information.
# Correction is not automated (no concrete inaccuracy to describe). Which of the
# others are checked is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
#
# DPOrganizer platform note: field `id`s are random per-portal-instance
# UUIDs and won't transfer to other DPOrganizer forms, but each field also
# carries a STABLE `data-test="portal-input-N"` attribute (0=US State,
# 1=Type of request, 2=Name, 3=Email, 4=Additional comments) — use
# data-test, not id, if this platform shows up again elsewhere in this
# repo. The CAPTCHA input is also stably `data-test="captchaInput"`.
#
# CAPTCHA is a classic distorted-text image CAPTCHA (not reCAPTCHA/
# Turnstile) with a "Regenerate captcha image" link if the text is
# unreadable — **CAPTCHA solution required**. "Additional comments" is a
# required free-text field; filled with a generic description of the
# request since the site doesn't ask anything more specific.
#
# Page elements (data-test attributes):
#   portal-input-0   "US State" react-select (California / Texas only)
#   portal-input-1   "Type of request" multi-select react-select -> RIGHT_MAP entries
#   portal-input-2   Name (first + last)
#   portal-input-3   Email
#   portal-input-4   "Additional comments" (required free text)
#   captchaInput     Distorted-text image CAPTCHA (manual)
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://portals.dporganizer.com/cbf39a0c-c047-4a7b-814d-c9d45754b4af"

# The form is only for residents of these states (its "US State" select offers only them).
SERVES_NO_LAW_STATES = False
PORTAL_STATES = ("California", "Texas")

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Know or Access", "Data portability"],
    Right.RIGHT_TO_OPT_OUT: [
        "Opt-out from Cross-Context Behavioral Advertising or Targeted Advertising",
        "Opt-out from Sales of Personal Information",
    ],
    Right.RIGHT_TO_DELETE: ["Erasure"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every "Type of request" option -> the Right it maps to (None = not automated).
PAGE_RIGHTS = {
    "Erasure": Right.RIGHT_TO_DELETE,
    "Data portability": Right.RIGHT_TO_ACCESS,
    "Correction": None,
    "Know or Access": Right.RIGHT_TO_ACCESS,
    "Opt-out from Cross-Context Behavioral Advertising or Targeted Advertising": Right.RIGHT_TO_OPT_OUT,
    "Opt-out from Sales of Personal Information": Right.RIGHT_TO_OPT_OUT,
}


async def _select_react_select_option(tab, input_index, option_text, super_scraper, description):
    field_input = await tab.find(
        xpath=f"//div[@data-test='portal-input-{input_index}']//input", raise_exc=False
    )
    if not field_input:
        print(f"{super_scraper.OOPS} {description} input not found")
        return
    await field_input.click()
    await asyncio.sleep(0.6)
    option = await tab.find(
        xpath=f"//*[starts-with(@id,'react-select-{input_index + 2}-option') and normalize-space()='{option_text}']",
        raise_exc=False,
    )
    if option:
        await option.click()
        await asyncio.sleep(0.4)
    else:
        print(f"{super_scraper.OOPS} {description} option '{option_text}' not found")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return
    if SuperScraper.bail_if_state_unsupported(globals()):
        return
    if SuperScraper.STATE not in PORTAL_STATES:
        print(f"SKIP preqin: portal only accepts {' / '.join(PORTAL_STATES)} residents "
              f"(STATE={SuperScraper.STATE!r}).")
        return

    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    request_types = [entry for right in rights for entry in RIGHT_MAP[right]]
    message = SuperScraper.request_statement(rights, broker="Preqin")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        await _select_react_select_option(tab, 0, SuperScraper.STATE, super_scraper, "US State")

        for request_type in request_types:
            await _select_react_select_option(tab, 1, request_type, super_scraper, "type of request")

        # close the still-open multi-select dropdown so it doesn't overlap
        # the fields below in the screenshot
        await tab.execute_script("document.activeElement && document.activeElement.blur();")

        # Unlike portal-input-0/1 (which wrap a react-select in a div),
        # portal-input-2/3/4 carry the data-test attribute directly on the
        # <input> element.
        name_field = await tab.find(xpath="//input[@data-test='portal-input-2']", raise_exc=False)
        if name_field:
            await name_field.click()
            await asyncio.sleep(0.4)
            await name_field.type_text(f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        else:
            print(f"{super_scraper.OOPS} Name field not found")

        email_field = await tab.find(xpath="//input[@data-test='portal-input-3']", raise_exc=False)
        if email_field:
            await email_field.click()
            await asyncio.sleep(0.4)
            await email_field.type_text(SuperScraper.EMAIL)
        else:
            print(f"{super_scraper.OOPS} Email field not found")

        comments_field = await tab.find(xpath="//input[@data-test='portal-input-4']", raise_exc=False)
        if comments_field:
            await comments_field.click()
            await asyncio.sleep(0.4)
            await comments_field.type_text(message)
        else:
            print(f"{super_scraper.OOPS} Additional comments field not found")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run")
        print(
            "\nRequest filled but NOT submitted — a distorted-text image CAPTCHA "
            "requires a manual solve before clicking Submit Request."
        )


asyncio.run(main())
