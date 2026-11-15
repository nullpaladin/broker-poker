from django.db import models


class ScraperRun(models.Model):
    STATUS = [("pending", "Pending"), ("running", "Running"), ("complete", "Complete"), ("cancelled", "Cancelled")]
    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    dry_run = models.BooleanField(default=True)
    delete_enabled = models.BooleanField(default=False)
    captcha_mode = models.CharField(max_length=10, default="solve")
    only_slugs = models.JSONField(null=True, blank=True)  # developer filter
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    cancel_requested = models.BooleanField(default=False)


class SiteRunStatus(models.Model):
    STATUS = [("pending", "Pending"), ("in_progress", "In progress"), ("waiting_captcha", "Waiting on you"),
              ("completed", "Completed"), ("failed", "Failed"), ("skipped", "Skipped")]
    run = models.ForeignKey(ScraperRun, related_name="sites", on_delete=models.CASCADE)
    slug = models.CharField(max_length=120)
    display_name = models.CharField(max_length=255)
    order = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS, default="pending")
    needs_human = models.BooleanField(default=False)
    note = models.TextField(blank=True)
    warnings = models.IntegerField(default=0)
    fields_available = models.JSONField(default=list)
    rights_used = models.JSONField(default=list)
    screenshots = models.JSONField(default=list)  # file names inside the site's run dir
    log_tail = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]
        unique_together = ("run", "slug")


class CaptchaSession(models.Model):
    """One row per pause (input()) a scraper hits."""
    site_run = models.ForeignKey(SiteRunStatus, related_name="captchas", on_delete=models.CASCADE)
    kind = models.CharField(max_length=10, default="continue")  # continue | text
    prompt = models.TextField(blank=True)
    status = models.CharField(max_length=10, default="waiting")  # waiting | answered | timed_out
    answer = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
