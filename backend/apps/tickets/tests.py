from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.organizations.models import Membership, Organization
from .models import Comment, Ticket


class TenantIsolationTests(TestCase):
    def setUp(self):
        self.acme = Organization.objects.create(name="Acme Corp", slug="acme")
        self.globex = Organization.objects.create(name="Globex", slug="globex")
        Ticket.objects.create(organization=self.acme, subject="Printer won't work")
        Ticket.objects.create(organization=self.globex, subject="Globex merger plans")
        self.adam = get_user_model().objects.create_user("adam", password="pw")
        Membership.objects.create(organization=self.acme, user=self.adam)
        self.client.force_login(self.adam)

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

    def test_comment_takes_its_org_from_its_ticket(self):
        globex_ticket = Ticket.objects.get(subject="Globex merger plans")
        comment = Comment.objects.create(
            organization=self.acme, ticket=globex_ticket, body="Who owns me?"
        )
        self.assertEqual(comment.organization, self.globex)            

    def test_non_member_cannot_list_another_orgs_tickets(self):
        gary = get_user_model().objects.create_user("gary", password="pw")
        Membership.objects.create(organization=self.globex, user=gary)
        self.client.force_login(gary)
        response = self.client.get("/api/orgs/acme/tickets/")
        self.assertEqual(response.status_code, 404)

    def test_viewer_cannot_create_a_ticket(self):
        vera = get_user_model().objects.create_user("vera", password="pw")
        Membership.objects.create(
            organization=self.acme, user=vera, role=Membership.Role.VIEWER
        )
        self.client.force_login(vera)
        response = self.client.post(
            "/api/orgs/acme/tickets/",
            {"subject": "Vera was here"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Ticket.objects.filter(subject="Vera was here").exists())

    def test_viewer_can_still_read_tickets(self):
        vera = get_user_model().objects.create_user("vera", password="pw")
        Membership.objects.create(
            organization=self.acme, user=vera, role=Membership.Role.VIEWER
        )
        self.client.force_login(vera)
        response = self.client.get("/api/orgs/acme/tickets/")
        self.assertEqual(response.status_code, 200)       