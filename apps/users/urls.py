from django.urls import include, path

from . import views

app_name = "users"

urlpatterns = [
    # dj-rest-auth
    path("", include("dj_rest_auth.urls")),
    path("registration/", include("dj_rest_auth.registration.urls")),
    # Custom endpoints
    path("me/", views.UserMeView.as_view(), name="user-me"),
    path("me/profile/", views.UserProfileView.as_view(), name="user-profile"),
    path("me/delete/", views.DeleteAccountView.as_view(), name="user-delete"),
]
