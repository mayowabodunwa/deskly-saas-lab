from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from apps.organizations.models import Membership, Organization
from apps.tickets.models import Ticket

DEMO_PASSWORD = "deskly-demo"  # local demo only, never a real password

class Command(BaseCommand):
    help = "Create demo organizations and tickets for local development."

    @transaction.atomic
    def handle(self, *args, **options):
        acme, _ = Organization.objects.get_or_create(
            slug="acme",
            defaults={"name": "Acme Corp"},
        )
        globex, _ = Organization.objects.get_or_create(
            slug="globex",
            defaults={"name": "Globex"},
        )

        Ticket.objects.get_or_create(
            organization=acme,
            subject="Printer won't work",
            defaults={"body": "The office printer jams on every third page."},
        )
        Ticket.objects.get_or_create(
            organization=acme,
            subject="Password reset",
            defaults={"body": "Cannot sign in to the payroll portal."},
        )
        Ticket.objects.get_or_create(
            organization=globex,
            subject="Globex merger plans - confidential",
            defaults={"body": "Do not share outside Globex."},
       )
        User = get_user_model()
        people = [
            ("olivia", acme, Membership.Role.OWNER),
            ("adam", acme, Membership.Role.AGENT),
            ("vera", acme, Membership.Role.VIEWER),
            ("gary", globex, Membership.Role.AGENT),
        ]
        for username, org, role in people:
            user, _ = User.objects.get_or_create(username=username)
            user.set_password(DEMO_PASSWORD)
            user.save()
            Membership.objects.update_or_create(
                organization=org,
                user=user,
                defaults={"role": role},
            )    


        self.stdout.write("Seeded demo data.")
