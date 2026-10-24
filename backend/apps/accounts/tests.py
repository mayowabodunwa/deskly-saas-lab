from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings


FAKE_GOOGLE = {
    "google": {
        "APP": {"client_id": "test-client-id", "secret": "test-secret"},
        "SCOPE": ["profile", "email"],
    }
}


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

 
@override_settings(SOCIALACCOUNT_PROVIDERS=FAKE_GOOGLE)
class GoogleSignInTests(TestCase):
    def test_get_does_not_start_a_google_login(self):
        # A plain link (GET) only shows a "Continue" page. Otherwise
        # another website could start a login in your browser.
        response = self.client.get("/accounts/google/login/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Location", response.headers)

    def test_post_sends_the_browser_to_google_with_our_callback(self):
        response = self.client.post("/accounts/google/login/")
        self.assertEqual(response.status_code, 302)
        google_url = response.headers["Location"]
        self.assertTrue(google_url.startswith("https://accounts.google.com/"))
        self.assertIn("client_id=test-client-id", google_url)
        # The address Google must send people back to (URL-encoded).
        self.assertIn("accounts%2Fgoogle%2Flogin%2Fcallback%2F", google_url)

    def test_nobody_can_sign_up(self):
        users_before = get_user_model().objects.count()
        self.client.post("/accounts/signup/", {
            "username": "intruder",
            "password1": "a-long-Password-123",
            "password2": "a-long-Password-123",
        })
        self.assertEqual(get_user_model().objects.count(), users_before)       