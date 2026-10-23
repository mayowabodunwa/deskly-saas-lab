from django.contrib.auth import get_user_model
from django.test import Client, TestCase


class LogoutCsrfTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("adam", password="pw")
        # This client checks CSRF, like a real browser session.
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.user)

    def test_logout_without_token_is_refused(self):
        response = self.client.post("/api/auth/logout/")
        self.assertEqual(response.status_code, 403)
        # Still logged in: the forged logout did nothing.
        self.assertEqual(self.client.get("/api/me/").status_code, 200)

    def test_logout_with_token_works(self):
        self.client.get("/api/auth/csrf/")
        token = self.client.cookies["csrftoken"].value
        response = self.client.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 204)
        # Logged out: "who am I?" is refused now.
        self.assertEqual(self.client.get("/api/me/").status_code, 403)