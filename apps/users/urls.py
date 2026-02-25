from django.urls import include, path

from . import views

app_name = "users"

urlpatterns = [
    # dj-rest-auth (login, logout, token refresh, password reset)
    path("", include("dj_rest_auth.urls")),
    path("registration/", include("dj_rest_auth.registration.urls")),
    # Custom user endpoints
    path("me/", views.UserMeView.as_view(), name="user-me"),
    path("me/profile/", views.UserProfileView.as_view(), name="user-profile"),
    path("me/change-password/", views.ChangePasswordView.as_view(), name="user-change-password"),
    path("me/rentals/", views.UserRentalHistoryView.as_view(), name="user-rental-history"),
    path("me/delete/", views.DeleteAccountView.as_view(), name="user-delete"),
]
