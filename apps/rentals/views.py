import uuid
from decimal import Decimal

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import IsAdminOrReadOnly, IsOwner

from .models import Console, Rental, RentalStatus, Review
from .serializers import (
    ConsoleDetailSerializer,
    ConsoleListSerializer,
    RentalCreateSerializer,
    RentalDetailSerializer,
    RentalListSerializer,
    ReviewSerializer,
)


class ConsoleViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve available consoles."""

    queryset = Console.objects.filter(is_active=True).prefetch_related("images")
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["console_type", "condition", "is_available"]
    search_fields = ["name", "description"]
    ordering_fields = ["daily_rate", "created_at", "name"]
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
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return RentalCreateSerializer
        if self.action in ("retrieve",):
            return RentalDetailSerializer
        return RentalListSerializer

    def perform_create(self, serializer):
        console = serializer.validated_data["console"]
        start_date = serializer.validated_data["start_date"]
        end_date = serializer.validated_data["end_date"]
        duration = (end_date - start_date).days

        total_amount = console.daily_rate * Decimal(duration)

        rental_number = f"CC-{uuid.uuid4().hex[:8].upper()}"

        serializer.save(
            user=self.request.user,
            daily_rate=console.daily_rate,
            total_amount=total_amount,
            security_deposit=console.security_deposit,
            rental_number=rental_number,
        )

        # Mark console as unavailable
        console.is_available = False
        console.save(update_fields=["is_available"])

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        rental = self.get_object()
        if rental.status not in (RentalStatus.PENDING, RentalStatus.CONFIRMED):
            return Response(
                {"detail": "Cannot cancel this rental."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        rental.status = RentalStatus.CANCELLED
        rental.save(update_fields=["status"])

        # Make console available again
        rental.console.is_available = True
        rental.console.save(update_fields=["is_available"])

        return Response({"detail": "Rental cancelled successfully."})


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
