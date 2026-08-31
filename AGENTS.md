# AGENTS.md — Broker Poker Agent Operating Manual

## Environment Setup

1. Working directory: `broker-poker/`
2. Activate virtualenv: `source venv/bin/activate`
3. Verify `.env` exists with: `FIRST_NAME`, `LAST_NAME`, `EMAIL`, `ADDRESS`, `CITY`, `STATE`, `ZIP_CODE`, `DATE_OF_BIRTH`, `PHONE_NUMBER`

## File Structure

```
broker-poker/
├── src/
│   ├── dsar/
│   │   ├── super_scraper.py              # Base class — use its methods, don't reinvent them
│   │   ├── template_scraper.py           # Copy this to start a new scraper
│   │   ├── blacklist.json                # Blacklisted fields per broker
│   │   ├── memory/                       # Completion records per broker
│   │   │   └── [broker_name]_memory.json
│   │   └── broker_sites/
│   │       └── [broker_name]/
│   │           └── [broker_name]_scraper.py
│   └── state_privacy_request_factory/
├── validation/                           # Screenshots & HTML snapshots
├── docs/                                 # Reference docs (look up when needed)
└── .env
```

## Site Exploration

### Step 1 — curl (try first, it's fast)
```bash
curl -sL <url> | grep -E "<(input|select|form|textarea)"
```
If form fields appear in the output, the page is server-rendered and you can build XPaths directly from the HTML.

### Step 2 — pydoll inspection script (JS SPAs)
If curl returns a shell with no form fields (e.g. `<app-root></app-root>` or a custom Angular/React element), the form is JS-rendered. Write a one-off inspection script:

```python
import asyncio, os, time
import dotenv
from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

dotenv.load_dotenv()

async def main():
    options = ChromiumOptions()
    options.binary_location = os.getenv("CHROMIUM_LOCATION")
    options.add_argument("--no-sandbox")
    options.add_argument("--headless=new")
    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to("https://example.com/form")
        time.sleep(5)
        html = await tab.page_source   # property — no parentheses
        with open("/tmp/rendered.html", "w") as f:
            f.write(html)

asyncio.run(main())
```

Then inspect `/tmp/rendered.html` for form fields and XPaths.

To reveal dropdown options, click the dropdown first, `time.sleep(1)`, then re-capture `page_source`. Use `execute_script` with `JSON.stringify(...)` to read DOM state:

```python
result = await tab.execute_script(
    "return JSON.stringify(Array.from(document.querySelectorAll('.option')).map(e => e.textContent.trim()));"
)
options_list = json.loads(result['result']['result']['value'])
```

## Creating a New Scraper

### Phase 0 — Prepare

```bash
source venv/bin/activate

# Copy template
cp src/dsar/template_scraper.py src/dsar/broker_sites/[broker_name]/[broker_name]_scraper.py
```

### Phase 1 — Site Analysis

Explore the target URL (see **Site Exploration** above). Document every form field:

| Field | Type | XPath/Selector | Required? | Maps to SuperScraper? |
|-------|------|----------------|-----------|----------------------|
| First Name | input | `//input[@name='first_name']` | Yes | `FIRST_NAME` |
| State | select | `//select[@id='state']` | Yes | `STATE` |
| Reason | textarea | `//textarea[@id='reason']` | No | No |

### Phase 2 — Implementation

Standard import pattern:

```python
import asyncio
import time
from src.dsar.super_scraper import SuperScraper
from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://broker-example.com/opt-out-form"

async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")  # required on this machine

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        time.sleep(5)

        await super_scraper.input_text_field(tab=tab, xpath="//input[@name='first_name']", text=SuperScraper.FIRST_NAME, sleep=1)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@name='email']", text=SuperScraper.EMAIL, sleep=1)
        await super_scraper.choose_dropdown_option_by_text(tab=tab, input_xpath="//select[@id='state']", dropdown_option_text="California", sleep=1)
        await super_scraper.click_item_by_text(tab=tab, text="Submit Request", sleep=2)

        await asyncio.sleep(3)

asyncio.run(main())
```

**Implementation order:** required text fields → dropdowns → checkboxes/radio → optional fields → submit.

### Phase 3 — Test & Validate

```bash
source venv/bin/activate
python src/dsar/broker_sites/[broker_name]/[broker_name]_scraper.py
```

Check output for:
- No "OOPS" / "was not found" messages
- Browser shows form filled correctly
- Validation files created in `validation/`

If an element fails: try an alternative selector, increase timeout, then blacklist after 3 consecutive failures. See `docs/error_handling.md`.

### Phase 4 — Blacklist Management

Blacklist a field when:
- It fails 3+ times
- It doesn't map to any SuperScraper env variable
- It's clearly optional or requires data not in `.env`
- CAPTCHA is required

See `docs/blacklist_management.md` for the full API and JSON schema.

### Phase 5 — Memory File

Create `src/dsar/memory/[broker_name]_memory.json`:

```json
{
  "broker_name": "broker-example",
  "url": "https://broker-example.com/opt-out-form",
  "completion_date": "YYYY-MM-DD",
  "fields_implemented": ["first_name", "last_name", "email", "state"],
  "blacklisted_fields": ["social_security_number"],
  "xpath_mappings": {
    "first_name": "//input[@name='fname']",
    "state": "//select[@id='state']"
  },
  "known_issues": [],
  "validation_files": [
    "validation/broker-example_completed.html",
    "validation/broker-example_screenshot.png"
  ],
  "status": "COMPLETE"
}
```

### Phase 6 — Wrap Up

Move to the next URL. Don't carry XPath selectors across broker sites — each site's DOM is independent.

---

## Checklist

### Pre-scraper
- [ ] `.env` verified
- [ ] Blacklist checked for this broker
- [ ] Template copied to correct path
- [ ] Form inspected in browser

### Development
- [ ] All required fields implemented
- [ ] Dropdowns, checkboxes handled
- [ ] Sleeps/waits added for dynamic content
- [ ] CAPTCHA handled (blacklisted and documented)
- [ ] Submit button wired

### Testing
- [ ] No "OOPS" errors in output
- [ ] Browser shows correctly filled form
- [ ] Validation HTML and screenshot saved

### Completion
- [ ] Memory file created
- [ ] Blacklist updated if needed
- [ ] Known issues documented

---

## Stop Conditions

Only stop for:
- Browser crashes 3+ consecutive times
- Legal/ethical violation discovered
- API/site completely unavailable (confirmed)
- User explicitly requests stop

For everything else: fix it, blacklist it, or document it — then continue.

---

## Quick Reference

| Task | Command |
|------|---------|
| Activate venv | `source venv/bin/activate` |
| Run a scraper | `python src/dsar/broker_sites/[broker]/[broker]_scraper.py` |
| Inspect a site (curl) | `curl -sL <url>` |
| Inspect a site (pydoll) | write a one-off script, see **Site Exploration** |

## SuperScraper Method Reference

| Method | Use Case |
|--------|----------|
| `input_text_field(tab, xpath, text, sleep, timeout)` | Fill text inputs |
| `choose_dropdown_option_by_xpath(tab, input_xpath, dropdown_item_xpath, sleep, double_click, timeout)` | Select dropdown by XPath |
| `choose_dropdown_option_by_text(tab, input_xpath, dropdown_option_text, sleep, double_click, timeout)` | Select dropdown by visible text |
| `click_item_by_text(tab, text, sleep, timeout)` | Click button/link by text |
| `click_item_by_xpath(tab, xpath, sleep, timeout)` | Click element by XPath |

---

## Reference Docs

| Doc | When to read |
|-----|-------------|
| `docs/pydoll_reference.md` | PyDoll API — element finding, interaction, screenshots, scrolling |
| `docs/error_handling.md` | Error recovery procedures by category |
| `docs/blacklist_management.md` | Blacklist JSON schema and helper functions |
| `docs/scraper_methodology.md` | Conceptual overview of the scraper development approach |
