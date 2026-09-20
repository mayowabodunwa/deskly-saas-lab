from django.core.management.base import BaseCommand
from django.db import transaction

from apps.organizations.models import Organization
from apps.tickets.models import Ticket


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

        self.stdout.write("Seeded demo data.")
