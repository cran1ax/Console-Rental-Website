import uuid
from decimal import Decimal

from django.db import models, transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import IsAdminOrReadOnly, IsOwner

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
    """CRUD operations for user rentals."""

    permission_classes = [permissions.IsAuthenticated, IsOwner]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status"]
    ordering_fields = ["created_at", "start_date"]
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

    @transaction.atomic
    def perform_create(self, serializer):
        console = serializer.validated_data["console"]
        start_date = serializer.validated_data["start_date"]
        end_date = serializer.validated_data["end_date"]
        games = serializer.validated_data.get("games", [])
        accessories = serializer.validated_data.get("accessories", [])

        duration = (end_date - start_date).days
        total_amount = console.daily_price * Decimal(duration)

        # Add game costs
        for game in games:
            total_amount += game.daily_price * Decimal(duration)

        # Add accessory costs
        for acc in accessories:
            total_amount += acc.price_per_day * Decimal(duration)

        rental_number = f"CC-{uuid.uuid4().hex[:8].upper()}"

        rental = serializer.save(
            user=self.request.user,
            daily_rate=console.daily_price,
            total_amount=total_amount,
            security_deposit=console.security_deposit,
            rental_number=rental_number,
        )

        # Decrement inventory
        Console.objects.filter(pk=console.pk).update(
            available_quantity=models.F("available_quantity") - 1
        )
        for game in games:
            Game.objects.filter(pk=game.pk).update(
                available_quantity=models.F("available_quantity") - 1
            )
        for acc in accessories:
            Accessory.objects.filter(pk=acc.pk).update(
                available_quantity=models.F("available_quantity") - 1
            )

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def cancel(self, request, pk=None):
        rental = self.get_object()
        if rental.status not in (RentalStatus.PENDING, RentalStatus.CONFIRMED):
            return Response(
                {"detail": "Cannot cancel this rental."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        rental.status = RentalStatus.CANCELLED
        rental.save(update_fields=["status"])

        # Restore inventory
        Console.objects.filter(pk=rental.console_id).update(
            available_quantity=models.F("available_quantity") + 1
        )
        for game in rental.games.all():
            Game.objects.filter(pk=game.pk).update(
                available_quantity=models.F("available_quantity") + 1
            )
        for acc in rental.accessories.all():
            Accessory.objects.filter(pk=acc.pk).update(
                available_quantity=models.F("available_quantity") + 1
            )

        return Response({"detail": "Rental cancelled successfully."})


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
