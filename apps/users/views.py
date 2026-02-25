"""
Users API Views
===============

Custom user-facing endpoints that complement dj-rest-auth
(login / logout / register / token refresh / password reset).

Endpoints
─────────
• ``GET|PUT|PATCH /me/``              → current user detail / update
• ``GET|PUT|PATCH /me/profile/``      → user profile (ID proof, Stripe ID)
• ``POST /me/change-password/``       → change password (requires old password)
• ``GET  /me/rentals/``               → authenticated user's rental history
• ``DELETE /me/delete/``              → soft-delete (deactivate) account
"""

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.rentals.filters import RentalFilter
from apps.rentals.models import Rental
from apps.rentals.serializers import RentalListSerializer

from .models import UserProfile
from .serializers import UserProfileSerializer, UserSerializer, UserUpdateSerializer


@extend_schema(tags=["Users"])
class UserMeView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/v1/auth/me/   → retrieve current user with nested profile
    PUT  /api/v1/auth/me/   → full update (full_name, phone, address, avatar)
    PATCH /api/v1/auth/me/  → partial update
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return UserUpdateSerializer
        return UserSerializer

    def get_object(self):
        return self.request.user


@extend_schema(tags=["Users"])
class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/v1/auth/me/profile/   → user profile (ID proof, Stripe ID)
    PUT  /api/v1/auth/me/profile/   → update profile
    PATCH /api/v1/auth/me/profile/  → partial update
    """

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


class ChangePasswordSerializer(serializers.Serializer):
    """Inline serializer for the change-password endpoint."""

    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value


@extend_schema(tags=["Users"])
class ChangePasswordView(APIView):
    """
    POST /api/v1/auth/me/change-password/

    Requires ``old_password`` and ``new_password``.
    The user stays logged in after the change.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])

        return Response(
            {"detail": "Password updated successfully."},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Users"])
class UserRentalHistoryView(generics.ListAPIView):
    """
    GET /api/v1/auth/me/rentals/

    Paginated, filterable rental history for the authenticated user.
    Supports the same filters as the main Rental endpoint
    (status, rental_type, payment_status, date ranges, etc.).
    """

    serializer_class = RentalListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = RentalFilter
    search_fields = ["rental_number"]
    ordering_fields = ["created_at", "rental_start_date", "total_price", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            Rental.objects
            .filter(user=self.request.user)
            .select_related("user", "console")
            .prefetch_related("games", "accessories")
        )


@extend_schema(tags=["Users"])
class DeleteAccountView(APIView):
    """
    DELETE /api/v1/auth/me/delete/

    Soft-deletes the user account by setting ``is_active = False``.
    The user's data is preserved but they can no longer log in.
    """

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        user = request.user
        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response(
            {"detail": "Account deactivated successfully."},
            status=status.HTTP_200_OK,
        )
