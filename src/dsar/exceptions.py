"""Shared exception types for the DSAR scrapers."""

from __future__ import annotations


class NotAutomatableError(RuntimeError):
    """A scraper cannot run unattended (e.g. a mid-run SMS/email OTP is required)."""


class HealthCheckError(RuntimeError):
    """A health-check assertion failed."""


class RequiredFieldError(HealthCheckError):
    """A required form field could not be filled / came back empty on a health check."""

    def __init__(self, fields):
        self.fields = list(fields)
        super().__init__(
            "required field(s) not filled: " + ", ".join(self.fields)
        )


class RightsChangedError(HealthCheckError):
    """The rights a form offers no longer match the scraper's ``PAGE_RIGHTS`` inventory."""

    def __init__(self, missing, new):
        self.missing = list(missing)
        self.new = list(new)
        parts = []
        if self.missing:
            parts.append("no longer offered: " + "; ".join(self.missing))
        if self.new:
            parts.append("NEW on the page (add to PAGE_RIGHTS): " + "; ".join(self.new))
        super().__init__("rights changed — " + " | ".join(parts))
