# `state_privacy_data.json` — the state → privacy-law map

`src/state_privacy_request_factory/state_privacy_data.json` is the single source
of truth for:

- 2-letter USPS abbreviations (both directions),
- whether a state has an active comprehensive consumer-privacy law,
- the law's short/full name and citation root,
- which canonical DSAR **right codes** that law grants (per-right statute cites
  where known).

It replaces the old `StateAbbreviation` and `StateHasPrivacyLaws` enums. Read it
through `src/state_privacy_request_factory/state_privacy_data.py` — never parse
the JSON directly elsewhere.

## Schema

```jsonc
{
  "right_codes": ["access", "delete", "correct", "portability",
                  "opt_out_sale_share", "opt_out_targeted_ads",
                  "opt_out_profiling", "know_third_parties", "limit_sensitive_pi"],
  "states": [
    {
      "state": "MINNESOTA",          // canonical UPPER name (spaces, not underscores)
      "state_title": "Minnesota",    // title case — matches .env STATE
      "abbreviation": "MN",
      "has_privacy_law": true,
      "law_name": "Minnesota Consumer Data Privacy Act",  // null for no-law states
      "law_short_name": "MCDPA",                          // null for no-law states
      "statute_cite": "Minn. Stat. 325M",                 // citation root; null for no-law
      "rights": ["access", "delete", ...],   // codes the law grants; [] for no-law states
      "right_citations": {                   // OPTIONAL, per-right cites (only MN is curated)
        "access": "Minn. Stat. 325M.14(e)", ...
      }
    }
  ]
}
```

## Loader API (`state_privacy_data.py`)

| Function | Returns |
|---|---|
| `get_state_info(name_or_code)` | frozen `StateInfo` (raises `UnknownStateError`) |
| `state_abbreviation(name)` | `"MN"` |
| `state_has_privacy_law(name)` | `bool` (unknown ⇒ `False`) |
| `law_name(name, *, short=False)` | `"Minnesota Consumer Data Privacy Act"` / `"MCDPA"` / `None` |
| `rights_available(name)` | `frozenset` of right codes (empty for no-law) |
| `statute_cite(name, right_code=None)` | per-right cite, or the law's citation root |
| `state_camel_key(name, *, suffix="Usa")` | `"rhodeIslandUsa"` (for SixFifty-style forms) |
| `RIGHT_CODES` | the canonical tuple |
| `ALL_STATES` | every `StateInfo`, ordered by title-case name |

`SuperScraper` re-exposes the common ones: `STATE_ABBREVIATED`, `LAW_FULL_NAME`,
`LAW_SHORT_NAME`, `state_has_privacy_law()`, `state_camel_key()`,
`state_law_citation()`, plus the rights logic (`wants()`, `rights_to_exercise()`,
`request_statement()`).

## Maintenance

- **50 states, no DC / territories** — parity with the old enums. Adding DC is a
  deliberate behavior change; do it in its own PR.
- Minnesota is the only fully-curated state (law + per-right cites, from
  `src/dsar/emails/mcdpa_email_template.txt`). Every other has-law state carries a
  best-effort `law_name` and a permissive generic `rights` list with no per-right
  cites. **`law_name` / `statute_cite` / `rights` outside Minnesota have not been
  legally reviewed.** Correct them here as laws change — same living-reference
  cadence as the README's per-site notes.
- `know_third_parties` (Right to List of *specific* Third Parties) is currently
  granted only to `MN` and `OR`.
- The frontend selects state from a dropdown, so the loader does not tolerate
  unknown names — it raises `UnknownStateError`.
