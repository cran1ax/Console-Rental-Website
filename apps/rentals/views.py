import logging

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import IsAdminOrReadOnly, IsOwner

from . import rental_service
from .models import Accessory, Console, Game, Rental, RentalStatus, Review
from .serializers import (
    AccessorySerializer,
    ConsoleDetailSerializer,
    ConsoleListSerializer,
    GameDetailSerializer,
    GameListSerializer,
    RentalCreateSerializer,
    RentalDetailSerializer,
    RentalListSerializer,
    ReviewSerializer,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# CONSOLE
# ═══════════════════════════════════════════════════════════════════

class ConsoleViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve available consoles."""

    queryset = Console.objects.filter(is_active=True).prefetch_related("images")
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["console_type", "condition_status"]
    search_fields = ["name", "description"]
    ordering_fields = ["daily_price", "created_at", "name"]
    ordering = ["-created_at"]
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ConsoleDetailSerializer
        return ConsoleListSerializer

    @action(detail=True, methods=["get"])
    def reviews(self, request, slug=None):
        console = self.get_object()
        reviews = Review.objects.filter(console=console).select_related("user")
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)


# ═══════════════════════════════════════════════════════════════════
# GAME
# ═══════════════════════════════════════════════════════════════════

class GameViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve available games."""

    queryset = Game.objects.filter(is_active=True)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["platform", "genre"]
    search_fields = ["title", "description"]
    ordering_fields = ["daily_price", "rating", "created_at", "title"]
    ordering = ["-created_at"]
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"

    def get_serializer_class(self):
        if self.action == "retrieve":
            return GameDetailSerializer
        return GameListSerializer


# ═══════════════════════════════════════════════════════════════════
# ACCESSORY
# ═══════════════════════════════════════════════════════════════════

class AccessoryViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve available accessories."""

    queryset = Accessory.objects.filter(is_active=True)
    serializer_class = AccessorySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category", "compatible_with"]
    search_fields = ["name", "description"]
    ordering_fields = ["price_per_day", "created_at", "name"]
    ordering = ["-created_at"]
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"


# ═══════════════════════════════════════════════════════════════════
# RENTAL
# ═══════════════════════════════════════════════════════════════════

class RentalViewSet(viewsets.ModelViewSet):
    """
    CRUD for user rentals.

    All business logic (pricing, stock, late fees) is delegated to
    ``rental_service``.  This view is intentionally thin.
    """

    permission_classes = [permissions.IsAuthenticated, IsOwner]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "rental_type", "payment_status"]
    ordering_fields = ["created_at", "rental_start_date"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            Rental.objects.filter(user=self.request.user)
            .select_related("console")
            .prefetch_related("games", "accessories")
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return RentalCreateSerializer
        if self.action in ("retrieve",):
            return RentalDetailSerializer
        return RentalListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        try:
            rental = rental_service.create_rental(
                user=request.user,
                console=data.get("console"),
                games=data.get("game_ids", []),
                accessories=data.get("accessory_ids", []),
                rental_type=data["rental_type"],
                rental_start_date=data["rental_start_date"],
                rental_end_date=data["rental_end_date"],
                delivery_option=data.get("delivery_option", "pickup"),
                delivery_address=data.get("delivery_address", ""),
                delivery_notes=data.get("delivery_notes", ""),
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            RentalDetailSerializer(rental).data,
            status=status.HTTP_201_CREATED,
        )

    # ── Return a rental ──────────────────────────────────────────
    @action(detail=True, methods=["post"])
    def return_rental(self, request, pk=None):
        rental = self.get_object()
        try:
            rental = rental_service.return_rental(rental)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(RentalDetailSerializer(rental).data)

    # ── Cancel a rental ──────────────────────────────────────────
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        rental = self.get_object()
        try:
            rental = rental_service.cancel_rental(rental)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "Rental cancelled successfully."})

    # ── Late fee preview ─────────────────────────────────────────
    @action(detail=True, methods=["get"])
    def late_fee(self, request, pk=None):
        rental = self.get_object()
        fee = rental_service.calculate_late_fee(rental)
        return Response({
            "rental_number": rental.rental_number,
            "overdue_days": rental.overdue_days,
            "late_fee": str(fee),
        })


# ═══════════════════════════════════════════════════════════════════
# REVIEW
# ═══════════════════════════════════════════════════════════════════

class ReviewCreateView(generics.CreateAPIView):
    """Create a review for a completed rental."""

    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        rental = serializer.validated_data["rental"]
        serializer.save(
            user=self.request.user,
            console=rental.console,
        )
