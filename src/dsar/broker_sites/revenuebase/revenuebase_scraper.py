# revenuebase.ai — Google Form (forms.gle short link). This form is
# DELETION-ONLY — its title is literally "Data Removal Request Form" and
# there's no Access/Opt-Out option anywhere, so the whole scraper is
# gated on REMOVE_INFORMATION (there's nothing to submit otherwise).
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
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

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
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    if not SuperScraper.REMOVE_INFORMATION:
        print(
            "revenuebase.ai's form only supports data deletion — skipping since "
            "REMOVE_INFORMATION is not set."
        )
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
        await tab.take_screenshot(path="resources/screenshots/revenuebase_dry_run.png")
        print("Screenshot saved to resources/screenshots/revenuebase_dry_run.png")

        if SuperScraper.DRY_RUN:
            print("DRY RUN: would submit data removal request")
            return

        await super_scraper.click_item_by_text(tab=tab, text="Submit", sleep=2)
        print("Submitted data removal request")


asyncio.run(main())
