from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "rentals"

router = DefaultRouter()
router.register(r"consoles", views.ConsoleViewSet, basename="console")
router.register(r"bookings", views.RentalViewSet, basename="rental")

urlpatterns = [
    path("", include(router.urls)),
    path("reviews/", views.ReviewCreateView.as_view(), name="review-create"),
]
