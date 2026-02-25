from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path(
        "create-intent/",
        views.CreatePaymentIntentView.as_view(),
        name="create-payment-intent",
    ),
    path("", views.PaymentListView.as_view(), name="payment-list"),
    path(
        "webhook/stripe/",
        views.StripeWebhookView.as_view(),
        name="stripe-webhook",
    ),
]
