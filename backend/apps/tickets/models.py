from django.db import models
from apps.organizations.models import Organization


class TenantQuerySet(models.QuerySet):
    """A safe way to look things up. Explained after you see it work."""

    def for_org(self, organization):
        return self.filter(organization=organization)


class Ticket(models.Model):
    """A support request. Someone has a problem."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        PENDING = "pending", "Pending"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="tickets",
    )
    subject = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.subject


class Comment(models.Model):
    """A reply on a ticket."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantQuerySet.as_manager()

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment on ticket {self.ticket_id}"