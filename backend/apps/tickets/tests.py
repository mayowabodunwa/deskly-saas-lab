from django.test import TestCase

from apps.organizations.models import Organization

from .models import Ticket


class TenantIsolationTests(TestCase):
    def setUp(self):
        self.acme = Organization.objects.create(name="Acme Corp", slug="acme")
        self.globex = Organization.objects.create(name="Globex", slug="globex")
        Ticket.objects.create(organization=self.acme, subject="Printer won't work")
        Ticket.objects.create(organization=self.globex, subject="Globex merger plans")

    def test_for_org_returns_only_that_orgs_tickets(self):
        subjects = [t.subject for t in Ticket.objects.for_org(self.acme)]
        self.assertEqual(subjects, ["Printer won't work"])


    def test_ticket_list_endpoint_is_scoped_to_the_url_org(self):
        response = self.client.get("/api/orgs/acme/tickets/")

        self.assertEqual(response.status_code, 200)
        subjects = [ticket["subject"] for ticket in response.json()]
        self.assertEqual(subjects, ["Printer won't work"])

    def test_posting_with_another_orgs_id_still_lands_in_the_url_org(self):
        response = self.client.post(
            "/api/orgs/acme/tickets/",
            {"subject": "Planted", "organization": self.globex.id},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        planted = Ticket.objects.get(subject="Planted")
        self.assertEqual(planted.organization, self.acme)        
