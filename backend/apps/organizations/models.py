from django.conf import settings
from django.db import models

class Organization(models.Model):
    """One customer company using Deskly.

    This is the tenant boundary: every piece of customer data in the system
    ultimately points back to a row in this table.
    """

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    plan = models.CharField(max_length=20, default="free")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class Membership(models.Model):
    """Links one person to one organization, with a role.

    The role lives on the relationship, not on the user: the same person can be
    an owner at one organization and a viewer at another.
    """

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        AGENT = "agent", "Agent"
        VIEWER = "viewer", "Viewer"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.AGENT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                name="unique_membership_per_org",
            ),
        ]

    def __str__(self):
        return f"{self.user} @ {self.organization} ({self.role})"    
