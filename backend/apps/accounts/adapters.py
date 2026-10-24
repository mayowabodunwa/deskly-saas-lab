from allauth.account.adapter import DefaultAccountAdapter

class NoSignupAdapter(DefaultAccountAdapter):
    # Deskly users are created by us, never by signing up.
    # This also closes Google sign-up: unknown emails are refused.
    def is_open_for_signup(self, request):
        return False