# Error Handling Guide for Autonomous Scraper Creation

## Philosophy
**Continue working unless catastrophic failure occurs.** Most errors are solvable without user intervention.

## Error Categories

### Category 1: Element Not Found (Most Common)

**Symptoms:**

```
OOPS! The input field with xpath //input[@name='email'] was not found.
```

**Recovery Steps:**
1. ✅ Check if element exists with different selector
   ```python
   # Try alternative selectors
   element = await tab.find(css_selector="input[name='email']", raise_exc=False)
   element = await tab.find(text="Email", raise_exc=False)
```


2. ✅ Wait longer for dynamic content
```
await asyncio.sleep(5)
# Or wait for visibility
await element.wait_until(is_visible=True, timeout=15)
```

3. ✅ Check page fully loaded
```python
html = await tab.page_source
if "Loading..." in html:
    await asyncio.sleep(10)
```

4. ✅ If still not found after 3 attempts → ADD TO BLACKLIST


**Decision Tree:**
```
Element not found?
├─ Try alternative selector → Found? → Continue
├─ Wait longer → Found? → Continue  
├─ Check blacklist → Already blacklisted? → Skip
└─ Still not found after 3 tries → Blacklist it
```

### Category 2: Form Submission Failures
**Symptoms:**

- No success message after submit
- Error modal appears
- Page reloads without confirmation

**Recovery Steps:**
1. ✅ Verify all required fields filled
```
# Check each required field has value
required_fields = ['first_name', 'last_name', 'email', 'state']
for field in required_fields:
    element = await tab.find(xpath=f"//input[@name='{field}']", raise_exc=False)
    if not element:
        print(f"Missing required field: {field}")
```


2. ✅ Check for validation errors on page
```
error_msg = await tab.find(
    class_name="error-message",
    raise_exc=False
)
if error_msg:
    error_text = await error_msg.text
    print(f"Validation error: {error_text}")
```

3. ✅ Try alternative submit method
```
# Try clicking submit button
await super_scraper.click_item_by_text(tab=tab, text="Submit")

# Or try form submission via JavaScript
await tab.evaluate("document.querySelector('form').submit()")
```

4. ✅ If submission consistently fails → Document in memory file, move on


### Category 3: CAPTCHA Detection
**Symptoms:**

- CAPTCHA image appears
- "Verify you're human" challenge
- reCAPTCHA widget visible

**Recovery Steps:**


1. ✅ Detect CAPTCHA presence
```
captcha = await tab.find(
    xpath="//img[contains(@src, 'captcha')]",
    timeout=5,
    raise_exc=False
)

recaptcha = await tab.find(
    text="verify you're human",
    timeout=5,
    raise_exc=False
)
```
2. ✅ Add to blacklist immediately
```
# Update blacklist.json
blacklist["broker.com"]["blacklisted_fields"].append("captcha_verification")
```
3. ✅ Document in memory file
```
{
  "known_issues": [
    "CAPTCHA present - requires manual handling or 2Captcha integration"
  ]
}
```
4. ✅ Continue with other fields (don't block entire scraper)


### Category 4: Timeout Errors
**Symptoms:**
```
TimeoutError: Element not found within 10 seconds
```

**Recovery Steps:**


1. ✅ Increase timeout for that element
```
await tab.find(xpath="//button", timeout=30)  # Was 10, now 30
```

2. ✅ Increase timeout for the specific project
```
BASE_TIMEOUT_IN_SECONDS=30
```


3. ✅ Add explicit waits before interaction
```
await asyncio.sleep(5)  # Before finding element
```


4. ✅ Check if page is loading slowly
```
# Monitor page load state
await tab.wait_for_load_state("networkidle")
```

### Category 5: JavaScript Errors
**Symptoms:**
- Console shows JS errors
- Form elements not interactive
- Page behaves unexpectedly

**Recovery Steps:**
1. ✅ Check browser console (if debugging)
```
# Note: Requires headless=False for visual inspection
```
2. ✅ Wait for JavaScript to execute
```
await asyncio.sleep(3)
await tab.evaluate("window.onload")
```
3. ✅ Refresh page and retry
```python
await tab.refresh()
await asyncio.sleep(5)
```
4. ✅ If persistent → Document in memory file, consider browser restart

### Category 6: Browser Crashes
**Symptoms:**

- Browser window closes unexpectedly
- Connection lost to Chrome
- PyDoll raises connection error

**Recovery Steps:**
1. ✅ Restart browser (CRASH COUNTER = 1)
```
# Close current session
await browser.close()

# Start fresh
async with Chrome(options=options) as browser:
    tab = await browser.start()
```
2. ✅ If crashes 3+ times → STOP and document
```
{
  "known_issues": [
    "Browser crashes repeatedly - may need Chrome update or different binary"
  ],
  "status": "BLOCKED"
}
```
3. ✅ Check Chrome binary location
```
options.binary_location = os.getenv("CHROMIUM_LOCATION")  # Verify this path exists
```

## Blacklist Decision Framework

### When to Blacklist a Field
| Condition | Action |
|-----------|--------|
| Field doesn't match any SuperScraper env var | ✅ Blacklist |
| Field causes 3+ consecutive failures | ✅ Blacklist |
| Field is clearly optional | ✅ Blacklist |
| CAPTCHA present | ✅ Blacklist |
| Field requires info not in .env | ✅ Blacklist + ask user ONCE |
| Field is required by law | ❌ Don't blacklist - fix implementation |

### Blacklist Entry Format
```
{
  "broker-domain.com": {
    "blacklisted_fields": [
      {
        "field_name": "social_security_number",
        "reason": "Not required for state privacy request",
        "date_added": "2026-04-25",
        "added_by": "autonomous_agent"
      }
    ],
    "notes": "California privacy law doesn't require SSN"
  }
}
```

## Escalation Matrix

### Level 1: Self-Resolve (95% of cases)

- Element not found → Try alternative selectors
- Timeout → Increase timeout values
- Minor errors → Retry with delays

### Level 2: Blacklist & Document (4% of cases)

- CAPTCHA
- Fields without matching env vars
- Optional fields causing issues

### Level 3: STOP & Document (1% of cases)

- Browser crashes 3+ times
- Legal/ethical violations discovered
- API completely unavailable (check with web_search)

### Validation Checklist After Error Recovery
After fixing any error, verify:

- No "OOPS" messages in output
- All required fields have values
- Form submission attempted
- Validation artifacts saved
- Memory file updated with issue/resolution

### Common Error Messages & Meanings
| Message | Meaning | Action |
|---------|---------|--------|
| "was not found" | Element selector incorrect | Try alternative selector |
| "TimeoutError" | Element took too long | Increase timeout or wait |
| "ConnectionRefusedError" | Browser disconnected | Restart browser |
| "AttributeError" | Wrong method call | Check PyDoll docs |
| "JSONDecodeError" | Invalid response | Check page loaded correctly |


## Reinforcement: Keep Working!
**Remember:**
- Most errors are solvable autonomously
- Blacklist is your friend - use it liberally
- Document everything in memory files
- Only stop for catastrophic failures
- Each error is a learning opportunity for future scrapers
