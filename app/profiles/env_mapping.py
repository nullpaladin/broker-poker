"""Profile data -> the environment variables SuperScraper reads at class-definition time.
Every variable is set explicitly (blank when unknown) so a developer's .env can never leak
into a run: load_dotenv() does not override variables that already exist."""
from __future__ import annotations

import os

# Profile/SuperScraper field names (SuperScraper reads these from the environment).
PROFILE_FIELDS = [
    "FIRST_NAME", "LAST_NAME", "EMAIL", "ADDRESS", "ADDRESS_LINE_TWO", "CITY", "STATE",
    "ZIP_CODE", "DATE_OF_BIRTH", "LAST_FOUR_SSN", "PHONE_NUMBER", "LINKEDIN_URL",
    "FACEBOOK_URL", "TWITTER_URL", "INSTAGRAM_URL", "JOB_TITLE", "COMPANY_NAME", "ADVERTISING_ID",
]
REQUIRED = ["FIRST_NAME", "LAST_NAME", "EMAIL", "ADDRESS", "CITY", "STATE", "ZIP_CODE", "PHONE_NUMBER"]
FIELD_LABELS = {
    "FIRST_NAME": "First name", "LAST_NAME": "Last name", "EMAIL": "Email", "ADDRESS": "Street address",
    "ADDRESS_LINE_TWO": "Address line 2", "CITY": "City", "STATE": "State", "ZIP_CODE": "ZIP code",
    "DATE_OF_BIRTH": "Date of birth (DD/MM/YYYY)", "LAST_FOUR_SSN": "Last 4 of SSN", "PHONE_NUMBER": "Phone number",
    "LINKEDIN_URL": "LinkedIn URL", "FACEBOOK_URL": "Facebook URL", "TWITTER_URL": "Twitter/X URL",
    "INSTAGRAM_URL": "Instagram URL", "JOB_TITLE": "Job title", "COMPANY_NAME": "Company",
    "ADVERTISING_ID": "Mobile advertising ID (MAID)",
}
# Variables that must never be inherited from the launching shell / .env.
_ALWAYS_BLANK = ["TWO_CAPTCHA_API_KEY", "2CAPTCHA_API_KEY", "REQUEST_DETAILS"]


def provided_fields(data: dict) -> list[str]:
    return [k for k in PROFILE_FIELDS if (data.get(k) or "").strip()]


def profile_to_env(data: dict, *, dry_run: bool, delete: bool, headless: bool,
                   base_env: dict | None = None) -> dict:
    env = dict(base_env if base_env is not None else os.environ)
    for k in PROFILE_FIELDS:
        env[k] = (data.get(k) or "").strip()
    for k in _ALWAYS_BLANK:
        env.pop(k, None)
    env["DRY_RUN"] = "True" if dry_run else "False"
    env["REMOVE_INFORMATION"] = "True" if delete else "False"
    env["HEADLESS_BROWSER_MODE"] = "True" if headless else "False"
    rights = ["RIGHT_TO_ACCESS", "RIGHT_TO_OPT_OUT", "RIGHT_TO_LIST_OF_THIRD_PARTIES"] + (["RIGHT_TO_DELETE"] if delete else [])
    env["RIGHTS_TO_EXERCISE"] = ",".join(rights)
    env["HEALTH_CHECK"] = "False"
    env["BP_HEADLESS"] = "1" if headless else "0"
    env.setdefault("CHROMIUM_LOCATION", os.environ.get("CHROMIUM_LOCATION", ""))
    return env


def import_dotenv(path) -> dict:
    """Read a .env file into a profile dict (quoted values and trailing comments handled)."""
    out = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        if v[:1] in "\"'" and v.count(v[0]) >= 2:
            v = v[1:v.index(v[0], 1)]
        else:
            v = v.split(" #")[0].strip()
        if k in PROFILE_FIELDS:
            out[k] = v
    return out
