# PyDoll API Reference for Agent

## Overview
PyDoll is an async Python library for Chromium browser automation via Chrome DevTools Protocol. No WebDriver required.

## Core Import Pattern
```python
import asyncio
from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
```

## Browser Initialization

### Basic Setup
```python
options = ChromiumOptions()
options.binary_location = os.getenv("CHROMIUM_LOCATION")
options.add_argument("--no-sandbox")  # required — AppArmor blocks sandbox on this machine

async with Chrome(options=options) as browser:
    tab = await browser.start()
    await tab.go_to("https://example.com")
    # ... your scraping logic ...
```

### Headless Mode
```python
options.add_argument("--headless=new")  # omit for visible browser (debugging)
```

## Element Finding Methods

### find() - Primary Element Locator
```
# Find single element (returns element object or None)
element = await tab.find(
    xpath="//input[@name='email']",  # XPath preferred
    timeout=10,                       # Seconds to wait
    raise_exc=False                   # Return None instead of raising
)

# Find multiple elements
elements = await tab.find(
    class_name="product-item",
    find_all=True,
    timeout=10
)
```

### Supported Selectors

|Type | Example | Use Case |
|-----|---------|----------|
| XPath | `//button[text()='Submit']` | Complex text matching, parent traversal |
| CSS | `.button-class` | Simple class selection |
| ID | `#submit-button` | Unique element identification |
| Text | `text="Click Here"` | Visible text matching |

### query() - Alternative Locator
```
element = await tab.query(
    ".product-item:nth-of-type(150)",  # CSS selector
    timeout=10
)
```

## Element Interaction Methods

### click()
```
await element.click()
```
### type_text() (via keyboard)
```
await tab.keyboard.type_text(text="Hello World")
```

### get_attribute()
```
value = element.get_attribute("value")
src = element.get_attribute("src")
href = element.get_attribute("href")
```

### wait_until()
```
await element.wait_until(
    is_visible=True,  # or is_enabled, is_disabled
    timeout=5
)
```

## Navigation Methods

### go_to()
```
await tab.go_to("https://example.com")
```

### Reload
```python
await tab.refresh()
```

## Content Extraction

### Get Page HTML
```python
# page_source is a property — no parentheses
html = await tab.page_source

# title is also a property
title = await tab.title

# Save to file
with open("page.html", "w", encoding="utf-8") as f:
    f.write(html)
```

### Get Element Text
```
text = await element.text
```

## Screenshot & Export

### Full Page Screenshot
```python
await tab.take_screenshot(path="full_page.png")
```

### PDF Export
```python
await tab.print_to_pdf(path="page.pdf")
```

## Scrolling

### Import Scroll Position
```
from pydoll.constants import ScrollPosition
```

### Scroll Methods
```
# Scroll down by pixels
await tab.scroll.by(ScrollPosition.DOWN, 500, smooth=True)

# Scroll to specific element
await element.scroll_into_view()
```

## Waiting & Timing

### Explicit Wait
```
await asyncio.sleep(3)  # Simple delay
```

### Wait for Element Visibility
```
element = await tab.find(xpath="//div[@id='content']", raise_exc=False)
if element:
    await element.wait_until(is_visible=True, timeout=10)
```

## Error Handling Patterns

### Safe Element Finding
```
element = await tab.find(
    xpath="//input[@name='email']",
    timeout=10,
    raise_exc=False  # Returns None instead of raising exception
)

if not element:
    print("Element not found - checking blacklist")
    # Add to blacklist or skip
```

### Timeout Configuration
```
# Global timeout in .env
BASE_TIMEOUT_IN_SECONDS = "15"

# Per-call override
await tab.find(xpath="//button", timeout=30)  # Longer timeout
```

## Common Patterns for DSAR Forms

### Pattern 1: Text Input Field
```
field = await tab.find(xpath="//input[@name='first_name']", raise_exc=False)
if field:
    await field.click()
    await tab.keyboard.type_text(SuperScraper.FIRST_NAME)
```

### Pattern 2: Dropdown Selection
```
# Option A: By XPath
dropdown = await tab.find(xpath="//select[@id='state']", raise_exc=False)
if dropdown:
    await dropdown.click()
    option = await tab.find(
        xpath="//select[@id='state']/option[@value='CA']",
        raise_exc=False
    )
    if option:
        await option.click()

# Option B: Use SuperScraper helper
await super_scraper.choose_dropdown_option_by_xpath(
    tab=tab,
    input_xpath="//select[@id='state']",
    dropdown_item_xpath="//select[@id='state']/option[@value='CA']",
    sleep=1
)
```

### Pattern 3: Submit Button
```
# By text
await super_scraper.click_item_by_text(
    tab=tab,
    text="Submit",
    sleep=2
)

# By XPath
await super_scraper.click_item_by_xpath(
    tab=tab,
    xpath="//button[@type='submit']",
    sleep=2
)
```

### Pattern 4: Form Validation Check
```
# After submission, check for success message
success_msg = await tab.find(
    text="Request submitted successfully",
    timeout=5,
    raise_exc=False
)

if success_msg:
    print("✅ Form submitted successfully")
else:
    print("⚠️ Submission status unknown")
```

## Debugging Tips

### Enable Console Logging
```
# In browser options
options.set_preference("devtools.console.enabled", True)
```

### Capture Network Requests
```
# Note: May require additional PyDoll configuration
# Check PyDoll docs for network interception
```

### View Page Source for XPath Discovery
```
html = await tab.content()
print(html)  # Manually inspect to build xpaths
```

## Performance Optimization

### Reduce Sleep Times
```
# Instead of fixed sleeps, wait for conditions
await element.wait_until(is_visible=True, timeout=5)
# Rather than: await asyncio.sleep(5)
```

### Parallel Tab Management
```
# For batch processing (advanced)
tabs = []
for url in urls:
    tab = await browser.start()
    await tab.go_to(url)
    tabs.append(tab)
```

## Resource Cleanup
### Proper Browser Shutdown
```
async with Chrome(options=options) as browser:
    # Your logic here
# Browser automatically closes when exiting context
```

### Manual Close (if needed)
```
await browser.close()
```

## Integration with SuperScraper

### Environment Variables from .env
```
import dotenv
import os

dotenv.load_dotenv()
FIRST_NAME = os.getenv("FIRST_NAME")
EMAIL = os.getenv("EMAIL")
# ... etc
```

### Using SuperScraper Methods
```
from src.dsar.super_scraper import SuperScraper

super_scraper = SuperScraper()

# All PyDoll interactions go through SuperScraper helpers
await super_scraper.input_text_field(tab=tab, xpath=..., text=SuperScraper.EMAIL)
```

## Troubleshooting Common Issues
|Issue | Solution |
|------|----------|
| Element not found | Try alternative selector, increase timeout, check page loaded |
|Click fails | Element may be hidden, scroll into view first |
| Dropdown not working | Try `double_click=True`, wait for options to appear |
| Page too slow | Increase timeout inside of individual scraper compared to `BASE_TIMEOUT_IN_SECONDS` from `.env` |
| CAPTCHA appears | Cannot automate, add to blacklist | 

## Official Resources

- PyDoll Docs: https://pydoll.tech/docs/
- GitHub: https://github.com/autoscrape-labs/pydoll
