"""Loader for ``state_privacy_data.json`` — the maintained state -> privacy-law map.

Replaces the former ``state_name_abbreviation.StateAbbreviation`` and
``states_that_have_privacy_laws.StateHasPrivacyLaws`` enums. Every lookup accepts
either a full state name (any case, spaces or underscores) or a 2-letter
abbreviation.

The data file is the single source of truth; edit it (via a PR / GitHub issue),
not this module, when a law changes. ``law_name`` / ``statute_cite`` / per-state
``rights`` for states other than Minnesota are best-effort and not legally
reviewed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

_DATA_FILE = Path(__file__).with_name("state_privacy_data.json")


class UnknownStateError(KeyError):
    """Raised when a state name / abbreviation is not in the data file."""


@dataclass(frozen=True)
class StateInfo:
    state: str                      # canonical upper-case name, e.g. "MINNESOTA"
    state_title: str                # title-case name, e.g. "Minnesota"
    abbreviation: str               # 2-letter USPS code, e.g. "MN"
    has_privacy_law: bool
    law_name: str | None            # full name, e.g. "Minnesota Consumer Data Privacy Act"
    law_short_name: str | None      # e.g. "MCDPA"
    statute_cite: str | None        # citation root, e.g. "Minn. Stat. 325M"
    rights: frozenset[str]          # canonical right codes the law grants
    right_citations: dict[str, str] # right code -> specific statute cite (may be empty)


@cache
def _raw() -> dict:
    with _DATA_FILE.open(encoding="utf-8") as fh:
        return json.load(fh)


@cache
def _by_key() -> dict[str, StateInfo]:
    index: dict[str, StateInfo] = {}
    for row in _raw()["states"]:
        info = StateInfo(
            state=row["state"],
            state_title=row["state_title"],
            abbreviation=row["abbreviation"],
            has_privacy_law=row["has_privacy_law"],
            law_name=row.get("law_name"),
            law_short_name=row.get("law_short_name"),
            statute_cite=row.get("statute_cite"),
            rights=frozenset(row.get("rights", ())),
            right_citations=dict(row.get("right_citations", {})),
        )
        index[_norm(info.state)] = info
        index[info.abbreviation.upper()] = info
    return index


def _norm(name: str) -> str:
    return name.strip().upper().replace("_", " ")


RIGHT_CODES: tuple[str, ...] = tuple(_raw()["right_codes"])


@cache
def all_states() -> list[StateInfo]:
    """Every state, ordered by title-case name."""
    seen: dict[str, StateInfo] = {v.abbreviation: v for v in _by_key().values()}
    return sorted(seen.values(), key=lambda i: i.state_title)


ALL_STATES: list[StateInfo] = all_states()


def get_state_info(state_name: str) -> StateInfo:
    """Look up a state by full name or 2-letter code. Raises ``UnknownStateError``."""
    try:
        return _by_key()[_norm(state_name)]
    except KeyError:
        raise UnknownStateError(state_name) from None


def state_abbreviation(state_name: str) -> str:
    return get_state_info(state_name).abbreviation


def state_has_privacy_law(state_name: str) -> bool:
    """True if the state has an active comprehensive consumer-privacy law.

    Unknown states return ``False`` rather than raising — callers use this as a
    yes/no gate, not an identity check.
    """
    try:
        return get_state_info(state_name).has_privacy_law
    except UnknownStateError:
        return False


def law_name(state_name: str, *, short: bool = False) -> str | None:
    info = get_state_info(state_name)
    return info.law_short_name if short else info.law_name


def rights_available(state_name: str) -> frozenset[str]:
    """Canonical right codes the state's law grants (empty for no-law states)."""
    try:
        return get_state_info(state_name).rights
    except UnknownStateError:
        return frozenset()


def statute_cite(state_name: str, right_code: str | None = None) -> str | None:
    """Statute citation for a right (falls back to the law's citation root)."""
    info = get_state_info(state_name)
    if right_code and right_code in info.right_citations:
        return info.right_citations[right_code]
    return info.statute_cite


def state_camel_key(state_name: str, *, suffix: str = "Usa") -> str:
    """``"Rhode Island" -> "rhodeIslandUsa"``  /  ``"California" -> "californiaUsa"``.

    First word lower-cased, subsequent words capitalised, concatenated, ``suffix``
    appended. Used for form vendors (e.g. SixFifty) that key options this way.
    """
    words = get_state_info(state_name).state_title.split()
    head, *tail = words
    return head.lower() + "".join(w.capitalize() for w in tail) + suffix
