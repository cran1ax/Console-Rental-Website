from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    # ── Checkout ─────────────────────────────────────────────────
    path(
        "checkout-session/",
        views.CreateCheckoutSessionView.as_view(),
        name="checkout-session",
    ),
    # ── Webhook ──────────────────────────────────────────────────
    path(
        "webhook/stripe/",
        views.StripeWebhookView.as_view(),
        name="stripe-webhook",
    ),
    # ── Payment list / detail ────────────────────────────────────
    path(
        "",
        views.PaymentListView.as_view(),
        name="payment-list",
    ),
    path(
        "<uuid:id>/",
        views.PaymentDetailView.as_view(),
        name="payment-detail",
    ),
    # ── Refund ───────────────────────────────────────────────────
    path(
        "<uuid:id>/refund/",
        views.RefundView.as_view(),
        name="payment-refund",
    ),
]
