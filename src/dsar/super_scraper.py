import time
import dotenv
import os
import random

from src.state_privacy_request_factory.state_name_abbreviation import StateAbbreviation


class SuperScraper:
    dotenv.load_dotenv()
    # System-related information
    # NOTE: compared against a stripped/upper-cased string rather than truthiness —
    # os.getenv("REMOVE_INFORMATION") returns the literal string "False" when the .env
    # value is False, and non-empty strings are truthy in Python, so `if REMOVE_INFORMATION`
    # would always be True regardless of the .env setting.
    REMOVE_INFORMATION = (os.getenv("REMOVE_INFORMATION") or "").strip().upper() in ("TRUE", "1", "YES")
    DRY_RUN = (os.getenv("DRY_RUN") or "True").strip().upper() in ("TRUE", "1", "YES")
    TWO_CAPTCHA_API_KEY = os.getenv("2CAPTCHA_API_KEY")
    REQUEST_DETAILS = "REQUEST_TEMPLATE_HERE"  # TODO: Move to factory
    BASE_TIMEOUT_IN_SECONDS = os.getenv("BASE_TIMEOUT_IN_SECONDS")
    CHROMIUM_LOCATION = os.getenv("CHROMIUM_LOCATION")

    # Personal information
    FIRST_NAME = os.getenv("FIRST_NAME")
    LAST_NAME = os.getenv("LAST_NAME")
    EMAIL = os.getenv("EMAIL")
    ADDRESS = os.getenv("ADDRESS")
    ADDRESS_LINE_TWO = os.getenv("ADDRESS_LINE_TWO")
    CITY = os.getenv("CITY")
    STATE = os.getenv("STATE")
    ZIP_CODE = os.getenv("ZIP_CODE")
    DATE_OF_BIRTH = os.getenv("DATE_OF_BIRTH")
    LAST_FOUR_SSN = os.getenv("LAST_FOUR_SSN")
    LINKEDIN_URL = os.getenv("LINKEDIN_URL")
    JOB_TITLE = os.getenv("JOB_TITLE")
    COMPANY_NAME = os.getenv("COMPANY_NAME")
    PHONE_NUMBER = os.getenv("PHONE_NUMBER")
    
    ADVERTISING_ID = os.getenv("ADVERTISING_ID")
    OOPS = ""

    def __init__(self):
        rand = random.randrange(start=1, stop=100)
        if rand == 100:
            SuperScraper.OOPS = "FUCK"
        elif SuperScraper.STATE.upper() != "MINNESOTA":
            SuperScraper.OOPS = "Oops!"
        elif rand % 2:
            SuperScraper.OOPS = "Ope!"
        else:
            SuperScraper.OOPS = "Uufda!"

    @staticmethod
    async def choose_dropdown_option_by_xpath(tab, input_xpath, dropdown_item_xpath, sleep=0, double_click=False, timeout=BASE_TIMEOUT_IN_SECONDS):
        input_field = await tab.find(
            xpath=input_xpath,
            timeout=timeout,
            raise_exc=False
        )
        if not input_field:
            print(f"{SuperScraper.OOPS} The input field with xpath {input_xpath} was not found.")
            return

        if sleep:
            time.sleep(sleep)

        await input_field.click()
        if double_click:
            await input_field.click()  # Sometimes need a double click for dropdown options to appear
        dropdown_option = await tab.find(
            xpath=dropdown_item_xpath,
            timeout=timeout,
            raise_exc=False
        )
        if not dropdown_option:
            print(f"{SuperScraper.OOPS} The dropdown option with xpath {dropdown_item_xpath} was not found.")
            return

        if sleep:
            time.sleep(sleep)

        await dropdown_option.click()

    @staticmethod
    async def choose_dropdown_option_by_text(tab, input_xpath, dropdown_option_text, sleep=0, double_click=False, timeout=BASE_TIMEOUT_IN_SECONDS):
        input_field = await tab.find(
            xpath=input_xpath,
            timeout=timeout,
            raise_exc=False
        )
        if not input_field:
            print(f"{SuperScraper.OOPS} The input field with xpath {input_xpath} was not found.")
            return

        if sleep:
            time.sleep(sleep)

        await input_field.click()
        if double_click:
            await input_field.click()

        await SuperScraper.click_item_by_text(tab=tab, text=dropdown_option_text)

    @staticmethod
    async def click_item_by_text(tab, text, sleep=0, timeout=BASE_TIMEOUT_IN_SECONDS):
        button = await tab.find(
            text=text,
            timeout=timeout,
            raise_exc=False
        )
        if not button:
            print(f"{SuperScraper.OOPS} The clickable element with text {text} was not found.")
            return

        if sleep:
            time.sleep(sleep)

        await button.click()

    @staticmethod
    async def click_item_by_xpath(tab, xpath, sleep=0, timeout=BASE_TIMEOUT_IN_SECONDS):
        button = await tab.find(
            xpath=xpath,
            timeout=timeout,
            raise_exc=False
        )
        if not button:
            print(f"{SuperScraper.OOPS} The clickable item with xpath {xpath} was not found.")
            return

        if sleep:
            time.sleep(sleep)

        await button.click()

    @staticmethod
    async def input_text_field(tab, xpath, text, sleep=0, timeout=BASE_TIMEOUT_IN_SECONDS):
        input_field = await tab.find(
            xpath=xpath,
            timeout=timeout,
            raise_exc=False
        )
        if not input_field:
            print(f"{SuperScraper.OOPS} The input field with xpath {xpath} was not found.")
            return

        if sleep:
            time.sleep(sleep)

        await input_field.click()
        await tab.keyboard.type_text(text=text)

    @staticmethod
    async def solve_captcha(tab, image_xpath, input_field_xpath, sleep=0, timeout=BASE_TIMEOUT_IN_SECONDS):
        captcha_image = await tab.find(
            xpath=image_xpath,
            timeout=timeout,
            raise_exc=False
        )
        if not captcha_image:
            print(f"{SuperScraper.OOPS} The captcha image with xpath {image_xpath} was not found.")
            return

        # TODO: need to integrate 2captcha
        if sleep:
            time.sleep(sleep)

        captcha_input_field = await tab.find(
            xpath=input_field_xpath,
            timeout=timeout,
            raise_exc=False
        )
        if not captcha_input_field:
            print(f"{SuperScraper.OOPS} The captcha image field with xpath {input_field_xpath} was not found.")

        await captcha_input_field.click()
        await tab.keyboard.type_text("Here's the solved captcha!")

        print(f"Here's where I do the captcha stuff: {captcha_image}")

    @staticmethod
    async def state_full_name_to_abbreviated(state_name: str) -> str:
        abbreviated_state = StateAbbreviation[state_name.upper()].value
        print(f"DEBUG: Abbreviation of full state {state_name} is {abbreviated_state}")
        return abbreviated_state
