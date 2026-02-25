from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Rental, RentalStatus


@receiver(post_save, sender=Rental)
def handle_rental_status_change(sender, instance, **kwargs):
    """Handle side effects when rental status changes."""
    if instance.status == RentalStatus.RETURNED:
        # Make console available again
        instance.console.is_available = True
        instance.console.save(update_fields=["is_available"])
