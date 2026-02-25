from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "rentals"

router = DefaultRouter()
router.register(r"consoles", views.ConsoleViewSet, basename="console")
router.register(r"games", views.GameViewSet, basename="game")
router.register(r"accessories", views.AccessoryViewSet, basename="accessory")
router.register(r"bookings", views.RentalViewSet, basename="rental")
router.register(r"reviews", views.ReviewViewSet, basename="review")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "availability/check/",
        views.AvailabilityCheckView.as_view(),
        name="availability-check",
    ),
]
