from django.contrib.auth import get_user_model
from django.test import TestCase
from .models import Membership, Organization


class MembersOnlyTests(TestCase):
    def setUp(self):
        self.acme = Organization.objects.create(name="Acme Corp", slug="acme")
        self.globex = Organization.objects.create(name="Globex", slug="globex")
        self.gary = get_user_model().objects.create_user("gary", password="pw")
        Membership.objects.create(organization=self.globex, user=self.gary)

    def test_member_can_see_their_own_org(self):
        self.client.force_login(self.gary)
        response = self.client.get("/api/orgs/globex/")
        self.assertEqual(response.status_code, 200)

    def test_non_member_gets_404(self):
        self.client.force_login(self.gary)
        response = self.client.get("/api/orgs/acme/")
        self.assertEqual(response.status_code, 404)

    def test_non_member_and_missing_org_look_the_same(self):
        self.client.force_login(self.gary)
        acme = self.client.get("/api/orgs/acme/")
        missing = self.client.get("/api/orgs/no-such-org/")
        self.assertEqual(acme.status_code, missing.status_code)
        self.assertEqual(acme.json(), missing.json())

    def test_anonymous_is_refused(self):
        response = self.client.get("/api/orgs/acme/")
        self.assertEqual(response.status_code, 403)