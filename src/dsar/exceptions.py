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
