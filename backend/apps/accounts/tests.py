from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings


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
        self.assertEqual(self.client.get("/api/me/").status_code, 401)

@override_settings(CACHES={
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
})
class LoginThrottleTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_sixth_login_attempt_in_a_minute_is_throttled(self):
        wrong_login = {"username": "olivia", "password": "wrong"}
        for attempt in range(5):
            response = self.client.post(
                "/api/auth/login/", wrong_login, content_type="application/json"
            )
            self.assertEqual(response.status_code, 400)

        response = self.client.post(
            "/api/auth/login/", wrong_login, content_type="application/json"
        )
        self.assertEqual(response.status_code, 429)
        # Tells the caller how long to wait.
        self.assertIn("Retry-After", response.headers)        

    def test_logged_in_caller_is_throttled_too(self):
        # An attacker logs into their own account first, then guesses.
        attacker = get_user_model().objects.create_user("mallory", password="pw")
        self.client.force_login(attacker)
        wrong_login = {"username": "olivia", "password": "wrong"}
        for attempt in range(5):
            self.client.post(
                "/api/auth/login/", wrong_login, content_type="application/json"
            )

        response = self.client.post(
            "/api/auth/login/", wrong_login, content_type="application/json"
        )
        self.assertEqual(response.status_code, 429)        