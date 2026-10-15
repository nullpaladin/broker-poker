# revenuebase.ai — Google Form (forms.gle short link). This form is
# DELETION-ONLY — its title is literally "Data Removal Request Form" and
# there's no Access/Opt-Out option anywhere, so RIGHT_MAP has only
# RIGHT_TO_DELETE (there's nothing to submit otherwise).
#
# Google Forms quirks (same platform as jobot.com/jungroup.com elsewhere
# in this repo, but this instance DOES expose stable `aria-label`s on its
# role="radio"/role="checkbox" elements, matching the visible option text —
# use those directly instead of the positional-index workaround needed on
# forms that lack them). Plain text inputs/textareas all share
# `jsname="YPqjbf"` with no per-field id — targeted positionally in DOM
# order: [0] top-level Email, [1] Full Legal Name, [2] Data Subject's
# Email Address, [3] State/Province (a plain text field despite following
# the Country question, NOT a dropdown). Country (Q4) is a custom
# combobox (role="listbox"/role="option", not a native <select>) — click
# it open, then click the matching option's `data-value`. "Any other
# emails/phones" (Q6), "Date of Last Known Interaction" (Q7), and the
# closing 1-5 satisfaction rating are all optional and skipped. "What is
# the primary reason for requesting data removal?" (Q8, multi-select
# checkboxes) — "Complying with a legal obligation (e.g., GDPR, CCPA,
# etc.)" checked, since that's the actual legal basis for an automated
# state-privacy-law deletion request. Both required "Confirmation of
# Understanding" checkboxes (Q10) are checked — true for a matching
# persona submitting their own real request.
#
# Page elements (Google Form, positional text inputs via TEXT_INPUT_XPATH):
#   text input [1]   top-level Email
#   radio            "Data Subject (The person whose data is being requested for removal)"
#   text input [2]   Full Legal Name
#   text input [3]   Data Subject's Email Address
#   role=listbox     Country combobox -> option "United States"
#   text input [4]   State/Province (plain text)
#   checkbox         "Complying with a legal obligation (e.g., GDPR, CCPA, etc.)" (removal reason)
#   checkbox x2      "Confirmation of Understanding" ("I understand that once my data is permanently
#                    removed..." / "I confirm that the information provided above is accurate...")
#   "Submit" text    Submit button
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

RIGHT_MAP = {Right.RIGHT_TO_DELETE: "Data Removal Request"}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

URL = "https://forms.gle/5Cab6bJcRtqVzAJS8"

TEXT_INPUT_XPATH = '(//input[@jsname="YPqjbf" and (@type="text" or @type="email")])[{index}]'


async def click_by_role_and_label(tab, super_scraper, role, aria_label, description):
    element = await tab.find(
        xpath=f"//*[@role='{role}' and @aria-label='{aria_label}']", raise_exc=False
    )
    if element:
        await element.click()
        await asyncio.sleep(0.3)
    else:
        print(f"{super_scraper.OOPS} {description} not found")


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form (it only supports deletion) — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(4)

        await super_scraper.input_text_field(
            tab=tab, xpath=TEXT_INPUT_XPATH.format(index=1), text=SuperScraper.EMAIL, sleep=0.3
        )
        await click_by_role_and_label(
            tab, super_scraper, "radio",
            "Data Subject (The person whose data is being requested for removal)",
            "'Who is submitting this request' radio",
        )
        await super_scraper.input_text_field(
            tab=tab,
            xpath=TEXT_INPUT_XPATH.format(index=2),
            text=f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}",
            sleep=0.3,
        )
        await super_scraper.input_text_field(
            tab=tab, xpath=TEXT_INPUT_XPATH.format(index=3), text=SuperScraper.EMAIL, sleep=0.3
        )

        country_listbox = await tab.find(xpath="//*[@role='listbox']", raise_exc=False)
        if country_listbox:
            await country_listbox.click()
            await asyncio.sleep(0.5)
            us_option = await tab.find(
                xpath="//*[@role='option' and @data-value='United States']", raise_exc=False
            )
            if us_option:
                await us_option.click()
                await asyncio.sleep(0.3)
            else:
                print(f"{super_scraper.OOPS} 'United States' country option not found")
        else:
            print(f"{super_scraper.OOPS} Country listbox not found")

        await super_scraper.input_text_field(
            tab=tab, xpath=TEXT_INPUT_XPATH.format(index=4), text=SuperScraper.STATE, sleep=0.3
        )

        await click_by_role_and_label(
            tab, super_scraper, "checkbox",
            "Complying with a legal obligation (e.g., GDPR, CCPA, etc.)",
            "removal-reason checkbox",
        )
        await click_by_role_and_label(
            tab, super_scraper, "checkbox",
            "I understand that once my data is permanently removed, Revenuebase may not be "
            "able to fulfill any future requests or services that rely on this data.",
            "'understand' confirmation checkbox",
        )
        await click_by_role_and_label(
            tab, super_scraper, "checkbox",
            "I confirm that the information provided above is accurate to the best of my knowledge.",
            "'confirm accurate' confirmation checkbox",
        )

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run_delete")
        if SuperScraper.DRY_RUN:
            print("DRY RUN: would submit data removal request")
            return

        await super_scraper.click_item_by_text(tab=tab, text="Submit", sleep=2)
        print(f"Submitted '{Right.RIGHT_TO_DELETE.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())
