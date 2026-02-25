from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings


class AccountAdapter(DefaultAccountAdapter):
    """Custom adapter for django-allauth."""

    def get_email_confirmation_url(self, request, emailconfirmation):
        """Override to point to frontend confirmation URL."""
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        return f"{frontend_url}/auth/verify-email/{emailconfirmation.key}"

    def send_mail(self, template_prefix, email, context):
        """Override to customize email sending."""
        context["site_name"] = "Corner Console"
        super().send_mail(template_prefix, email, context)
