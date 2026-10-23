# verizon.com — the Visible.com/privacyportal page (Visible is a Verizon
# prepaid brand) only offers "Member Portal"/"Former Member"/"Agent Portal"
# (all login-required) plus a link to Verizon's own "privacy inquiry form."
# That in turn points non-account-holders to a guest privacy dashboard
# (verizon.com/privacy/your-data/guest-landing → "I've never been a
# customer" → download/delete wizards) — but BOTH of those wizards only
# collect an email address before immediately sending a one-time
# authorization code and blocking on it (an email/OTP wall this repo
# doesn't automate past, same precedent as statsocial.com), so there is
# almost nothing to fill there.
#
# Instead this scraper targets the actual multi-purpose Drupal webform at
# verizon.com/about/privacy/privacy-inquiries, which explicitly serves
# "Anyone that would like to submit questions about Verizon's privacy
# policies or practices" and non-account-holders, with no OTP gate.
#
# This is a heavily conditional Drupal webform: almost none of the radio/
# checkbox inputs respond to a plain pydoll `.click()` (the click does not
# toggle `.checked` — likely a custom-styled input intercepting the click
# target) — set `.checked = true` and dispatch both 'change' and 'click'
# events via JS instead, which is what actually triggers Drupal's
# show/hide conditional logic.
#
# "Relationship to Verizon" answered "I was never a customer." (closest
# fit for this repo's generic consumer persona). That reveals "Tell us
# more about your inquiry" — a SECOND single-select radio group — answered
# "I would like to request a download or deletion of personal information
# (select all that apply)." which in turn reveals a checkbox pair, Download
# (maps to Right.RIGHT_TO_ACCESS) and Deletion (maps to Right.RIGHT_TO_DELETE); which of them
# are checked is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP) —
# both checkboxes share the SAME element ids across every "tell us more"
# variant that offers them (id="edit-select-download"/"edit-select-
# deletion"), so no per-variant lookup is needed. Selecting this option
# also removes the "Provide a detailed summary" requirement (visually
# hidden) in favor of the checkboxes. Phone Number requires first choosing
# "Mobile phone number" (a radio) before its text field becomes enabled.
# Home state select values are formatted "XX - Full Name" (matched by
# substring). Distorted-text image CAPTCHA — **CAPTCHA solution
# required**.
#
# Page elements:
#   #edit-name                                 First name
#   #edit-last-name-                           Last name
#   #edit-email-address-mail-1 / -mail-2       Email / Confirm email
#   #edit-checkbox-mobile-phone-number         "Mobile phone number" radio (enables the phone field)
#   #edit-mobile-phone-number                  Phone number (10 digits, no formatting)
#   #edit-home-state                           Home state <select> ("XX - Full Name")
#   #edit-brand                                Brand <select> (-> "Verizon")
#   #edit-relationship-to-verizon-radios-i-was-never-a-customer   "I was never a customer." radio
#   #edit-tell-us-more-about-your-inquiry-...-select-all-that-apply   "I would like to request a
#                                              download or deletion of personal information" radio
#   #edit-select-download                      "Download" checkbox
#   #edit-select-deletion                      "Deletion" checkbox
#   Distorted-text image CAPTCHA (manual entry)
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://www.verizon.com/about/privacy/privacy-inquiries"

DOWNLOAD_CHECKBOX = "edit-select-download"  # "Download"
DELETION_CHECKBOX = "edit-select-deletion"  # "Deletion"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: DOWNLOAD_CHECKBOX,
    Right.RIGHT_TO_DELETE: DELETION_CHECKBOX,
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every option in the download/deletion checkbox pair, as displayed -> the Right it maps to. The pair is revealed only after
# the relationship and inquiry radios are chosen.
PAGE_RIGHTS = {"Download": Right.RIGHT_TO_ACCESS, "Deletion": Right.RIGHT_TO_DELETE}
RIGHTS_OPTIONS_CSS = (
    "label:has(#edit-select-download), label:has(#edit-select-deletion), "
    "label[for='edit-select-download'], label[for='edit-select-deletion']"
)  # built from the two recorded checkbox ids

FIELD_XPATHS = {
    "First name": "//*[@id='edit-name']",
    "Last name": "//*[@id='edit-last-name-']",
    "Email": "//*[@id='edit-email-address-mail-1']",
    "Confirm email": "//*[@id='edit-email-address-mail-2']",
    "Home state": "//*[@id='edit-home-state']",
    "Brand": "//*[@id='edit-brand']",
}


async def _click_via_js(tab, super_scraper, element_id, description):
    element = await tab.find(id=element_id, raise_exc=False)
    if element:
        await element.execute_script(
            "this.checked = true;"
            "this.dispatchEvent(new Event('change', {bubbles:true}));"
            "this.dispatchEvent(new Event('click', {bubbles:true}));"
        )
        await asyncio.sleep(0.8)
    else:
        print(f"{super_scraper.OOPS} '{description}' element not found")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        text_fields = {
            "edit-name": SuperScraper.FIRST_NAME,
            "edit-last-name-": SuperScraper.LAST_NAME,
            "edit-email-address-mail-1": SuperScraper.EMAIL,
            "edit-email-address-mail-2": SuperScraper.EMAIL,
        }
        for field_id, value in text_fields.items():
            field = await tab.find(id=field_id, raise_exc=False)
            if field:
                await field.type_text(value)
            else:
                print(f"{super_scraper.OOPS} field '{field_id}' not found")

        await _click_via_js(tab, super_scraper, "edit-checkbox-mobile-phone-number", "Mobile phone number radio")
        if SuperScraper.PHONE_NUMBER:
            phone_field = await tab.find(id="edit-mobile-phone-number", raise_exc=False)
            if phone_field:
                # Field requires exactly 10 digits, no formatting characters.
                digits_only = "".join(c for c in SuperScraper.PHONE_NUMBER if c.isdigit())
                await phone_field.type_text(digits_only)
            else:
                print(f"{super_scraper.OOPS} Mobile phone number field not found")

        state_select = await tab.find(id="edit-home-state", raise_exc=False)
        if state_select:
            await state_select.execute_script(
                "for (var i=0;i<this.options.length;i++){"
                f"  if(this.options[i].value.indexOf({SuperScraper.STATE!r})!==-1){{ this.selectedIndex=i; }}"
                "}"
                "this.dispatchEvent(new Event('change', {bubbles:true}));"
            )
        else:
            print(f"{super_scraper.OOPS} Home state select not found")

        brand_select = await tab.find(id="edit-brand", raise_exc=False)
        if brand_select:
            await brand_select.execute_script(
                "for (var i=0;i<this.options.length;i++){"
                "  if(this.options[i].value==='Verizon'){ this.selectedIndex=i; }"
                "}"
                "this.dispatchEvent(new Event('change', {bubbles:true}));"
            )
        else:
            print(f"{super_scraper.OOPS} Brand select not found")

        await _click_via_js(
            tab, super_scraper, "edit-relationship-to-verizon-radios-i-was-never-a-customer", "Relationship to Verizon"
        )
        await _click_via_js(
            tab,
            super_scraper,
            "edit-tell-us-more-about-your-inquiry-i-would-like-to-request-a-download-or-deletion-of-personal-information-select-all-that-apply",
            "Tell us more about your inquiry",
        )
        if SuperScraper.HEALTH_CHECK:
            offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
            SuperScraper.audit_rights(offered, PAGE_RIGHTS)

        for right in rights:
            await _click_via_js(tab, super_scraper, RIGHT_MAP[right], f"{right.name} checkbox")

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run")
        print(
            "\nRequest filled but NOT submitted — a distorted-text image CAPTCHA requires "
            "manual entry before submitting."
        )


asyncio.run(main())
