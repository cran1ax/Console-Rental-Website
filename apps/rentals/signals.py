from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Accessory, Console, Game, Rental, RentalStatus


@receiver(post_save, sender=Rental)
def handle_rental_returned(sender, instance, **kwargs):
    """Restore inventory when a rental is marked as returned."""
    if instance.status == RentalStatus.RETURNED:
        Console.objects.filter(pk=instance.console_id).update(
            available_quantity=models.F("available_quantity") + 1
        )
        for game in instance.games.all():
            Game.objects.filter(pk=game.pk).update(
                available_quantity=models.F("available_quantity") + 1
            )
        for acc in instance.accessories.all():
            Accessory.objects.filter(pk=acc.pk).update(
                available_quantity=models.F("available_quantity") + 1
            )
