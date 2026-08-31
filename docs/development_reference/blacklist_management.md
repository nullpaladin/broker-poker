# Blacklist Management System

## Purpose
The blacklist prevents the agent from repeatedly attempting to fill fields that cannot be populated with available SuperScraper data or that cause consistent failures.

## File Location
```
src/dsar/blacklist.json
```

## Structure

### Root Level
```
{
  "broker-domain.com": {
    "blacklisted_fields": [],
    "notes": "",
    "last_updated": "2026-04-25"
  }
}
```
### Field Entry Format
```
{
  "field_name": "social_security_number",
  "reason": "Not required for state privacy requests",
  "date_added": "2026-04-25",
  "added_by": "autonomous_agent",
  "failure_count": 3
}
```

## Adding Fields to Blacklist

### Automated Process (Agent Should Do This)
```
import json
from datetime import datetime

def add_to_blacklist(broker_domain, field_name, reason):
    """Add field to blacklist automatically"""
    
    # Load existing blacklist
    try:
        with open('src/dsar/blacklist.json', 'r') as f:
            blacklist = json.load(f)
    except FileNotFoundError:
        blacklist = {}
    
    # Initialize broker entry if needed
    if broker_domain not in blacklist:
        blacklist[broker_domain] = {
            "blacklisted_fields": [],
            "notes": "",
            "last_updated": datetime.now().strftime("%Y-%m-%d")
        }
    
    # Check if already blacklisted
    existing = next(
        (f for f in blacklist[broker_domain]["blacklisted_fields"] 
         if f["field_name"] == field_name),
        None
    )
    
    if existing:
        existing["failure_count"] = existing.get("failure_count", 0) + 1
    else:
        blacklist[broker_domain]["blacklisted_fields"].append({
            "field_name": field_name,
            "reason": reason,
            "date_added": datetime.now().strftime("%Y-%m-%d"),
            "added_by": "autonomous_agent",
            "failure_count": 1
        })
    
    # Save updated blacklist
    blacklist[broker_domain]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    
    with open('src/dsar/blacklist.json', 'w') as f:
        json.dump(blacklist, f, indent=2)
    
    print(f"✅ Added '{field_name}' to blacklist for {broker_domain}")
```

### Checking Blacklist Before Implementation
```
def is_field_blacklisted(broker_domain, field_name):
    """Check if field is blacklisted for specific broker"""
    try:
        with open('src/dsar/blacklist.json', 'r') as f:
            blacklist = json.load(f)
        
        broker_data = blacklist.get(broker_domain, {})
        blacklisted = broker_data.get("blacklisted_fields", [])
        
        return any(field["field_name"] == field_name for field in blacklisted)
    except FileNotFoundError:
        return False
```

### Usage in Scraper
```
# Before implementing field
if is_field_blacklisted("broker.com", "social_security_number"):
    print("⚠️ Field blacklisted - skipping")
    continue

# After 3 failed attempts
if failure_count >= 3:
    add_to_blacklist(
        broker_domain="broker.com",
        field_name="social_security_number",
        reason="Failed 3 consecutive times - not in SuperScraper env vars"
    )
    print("✅ Field added to blacklist - continuing")
```

### Common Blacklist Reasons
| Reason | When to Use |
|--------|-------------|
|"Not in SuperScraper env vars" | Field requires data not available in .env |
|"Optional field" | Field not required by law or form |
|"CAPTCHA present" | Field requires human verification |
|"Failed X consecutive times" | Field causes repeated errors |
|"Not required for state privacy" | Legal requirement doesn't apply |
| "Dynamic field" | Field changes per session, unreliable |

## Blacklist Review Process

### Weekly Review (Human)

- Review all blacklisted fields
- Remove fields that can now be implemented
- Update reasons if needed
- Check for patterns across brokers

### Auto-Cleanup Rules
Fields should be removed from blacklist if:
1. SuperScraper env vars updated to include the data
2. Form structure changed (field no longer exists)
3. Legal requirements updated (field now optional)

### Example Blacklist File (Complete)
```
{
  "delete-me-now.com": {
    "blacklisted_fields": [
      {
        "field_name": "social_security_number",
        "reason": "Not required for California privacy request",
        "date_added": "2026-04-20",
        "added_by": "autonomous_agent",
        "failure_count": 5
      },
      {
        "field_name": "mother_maiden_name",
        "reason": "Security question - cannot be automated",
        "date_added": "2026-04-21",
        "added_by": "autonomous_agent",
        "failure_count": 3
      }
    ],
    "notes": "California privacy law doesn't require SSN or security questions",
    "last_updated": "2026-04-21"
  },
  "optout-manual.com": {
    "blacklisted_fields": [
      {
        "field_name": "captcha_verification",
        "reason": "reCAPTCHA v3 present - requires 2Captcha integration",
        "date_added": "2026-04-22",
        "added_by": "autonomous_agent",
        "failure_count": 1
      },
      {
        "field_name": "phone_number_verification",
        "reason": "SMS verification code required - cannot automate",
        "date_added": "2026-04-22",
        "added_by": "autonomous_agent",
        "failure_count": 2
      }
    ],
    "notes": "Requires manual phone verification step",
    "last_updated": "2026-04-22"
  },
  "data-removal-service.net": {
    "blacklisted_fields": [
      {
        "field_name": "employment_history",
        "reason": "Not required for basic privacy opt-out",
        "date_added": "2026-04-18",
        "added_by": "autonomous_agent",
        "failure_count": 4
      },
      {
        "field_name": "income_bracket",
        "reason": "Irrelevant for data deletion request",
        "date_added": "2026-04-18",
        "added_by": "autonomous_agent",
        "failure_count": 4
      }
    ],
    "notes": "These fields are marketing questions, not legal requirements",
    "last_updated": "2026-04-18"
  }
}
```

## Blacklist Statistics Tracking

### Optional: Track Blacklist Metrics
```
def get_blacklist_stats():
    """Get statistics about blacklist usage"""
    try:
        with open('src/dsar/blacklist.json', 'r') as f:
            blacklist = json.load(f)
        
        total_brokers = len(blacklist)
        total_blacklisted_fields = sum(
            len(data["blacklisted_fields"]) 
            for data in blacklist.values()
        )
        avg_failures = sum(
            field["failure_count"]
            for broker in blacklist.values()
            for field in broker["blacklisted_fields"]
        ) / max(total_blacklisted_fields, 1)
        
        return {
            "total_brokers_with_blacklist": total_brokers,
            "total_blacklisted_fields": total_blacklisted_fields,
            "average_failures_per_field": round(avg_failures, 2)
        }
    except FileNotFoundError:
        return {
            "total_brokers_with_blacklist": 0,
            "total_blacklisted_fields": 0,
            "average_failures_per_field": 0
        }
```

## Integration with Memory Files

### Linking Blacklist to Memory
When creating memory files, reference blacklist entries:
```
{
  "broker_name": "delete-me-now",
  "url": "https://delete-me-now.com/dsar",
  "completion_date": "2026-04-25",
  "fields_implemented": [
    "first_name",
    "last_name",
    "email",
    "state",
    "reason"
  ],
  "blacklisted_fields": [
    {
      "field_name": "social_security_number",
      "reference": "blacklist.json#delete-me-now.com.blacklisted_fields[0]"
    },
    {
      "field_name": "mother_maiden_name",
      "reference": "blacklist.json#delete-me-now.com.blacklisted_fields[1]"
    }
  ],
  "xpath_mappings": {
    "first_name": "//input[@name='fname']",
    "state": "//select[@id='state-select']"
  },
  "known_issues": [
    "CAPTCHA requires 2Captcha integration",
    "Form sometimes times out - increased timeout to 30s"
  ],
  "validation_files": [
    "validation/delete-me-now_completed.html",
    "validation/delete-me-now_screenshot.png"
  ]
}
```

## Migration Notes

### From Old Format to New Format
If you encounter old blacklist format:
```
// OLD FORMAT (deprecated)
{
  "broker.com": ["field1", "field2", "field3"]
}

// NEW FORMAT (current)
{
  "broker.com": {
    "blacklisted_fields": [
      {
        "field_name": "field1",
        "reason": "...",
        "date_added": "2026-04-25",
        "added_by": "autonomous_agent",
        "failure_count": 1
      }
    ],
    "notes": "...",
    "last_updated": "2026-04-25"
  }
}
```

### Migration Script
```
def migrate_old_blacklist_format():
    """Convert old blacklist format to new format"""
    try:
        with open('src/dsar/blacklist.json', 'r') as f:
            old_blacklist = json.load(f)
        
        new_blacklist = {}
        for broker, fields in old_blacklist.items():
            new_blacklist[broker] = {
                "blacklisted_fields": [
                    {
                        "field_name": field,
                        "reason": "Migrated from old format",
                        "date_added": "2026-04-25",
                        "added_by": "migration_script",
                        "failure_count": 0
                    }
                    for field in fields
                ],
                "notes": "Format migrated from array to structured format",
                "last_updated": "2026-04-25"
            }
        
        with open('src/dsar/blacklist.json', 'w') as f:
            json.dump(new_blacklist, f, indent=2)
        
        print("✅ Blacklist format migrated successfully")
    except FileNotFoundError:
        print("ℹ️ No existing blacklist to migrate")
```

## Best Practices

1. **Be Specific:** Include detailed reasons for blacklisting
2. **Track Failures:** Increment failure_count for pattern recognition
3. **Document Notes:** Add broker-specific context in notes field
4. **Date Everything:** Track when fields were added/removed
5. **Review Regularly:** Clean up outdated blacklist entries
6. **Don't Over-Blacklist:** Only blacklist after 3+ failures
7. **Link to Memory:** Reference blacklist in memory files for traceability

