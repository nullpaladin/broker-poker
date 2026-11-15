from django.db import models


class SubmittedRequest(models.Model):
    """Permanent ledger: one row per broker that has ever been launched for a REAL submission.
    Written BEFORE the launch so a crash can never lead to a duplicate DSAR. Deleting a row is a
    deliberate manual action (Submission history screen)."""
    slug = models.CharField(max_length=120, unique=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    run_id = models.IntegerField(null=True, blank=True)
