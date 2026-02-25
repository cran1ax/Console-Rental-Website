from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.rentals.models import Console, ConsoleCondition, ConsoleType


class Command(BaseCommand):
    help = "Seed database with sample consoles"

    def handle(self, *args, **options):
        consoles = [
            {
                "name": "PlayStation 5 Standard",
                "console_type": ConsoleType.PS5,
                "description": "Latest PS5 with disc drive. Comes with 1 DualSense controller.",
                "condition": ConsoleCondition.EXCELLENT,
                "serial_number": "PS5-STD-001",
                "daily_rate": Decimal("299.00"),
                "weekly_rate": Decimal("1799.00"),
                "monthly_rate": Decimal("5999.00"),
                "security_deposit": Decimal("5000.00"),
                "includes_controller": 1,
                "includes_games": False,
            },
            {
                "name": "PlayStation 5 Digital Edition",
                "console_type": ConsoleType.PS5_DIGITAL,
                "description": "PS5 Digital Edition - no disc drive. Comes with 1 DualSense controller.",
                "condition": ConsoleCondition.EXCELLENT,
                "serial_number": "PS5-DIG-001",
                "daily_rate": Decimal("249.00"),
                "weekly_rate": Decimal("1499.00"),
                "monthly_rate": Decimal("4999.00"),
                "security_deposit": Decimal("4000.00"),
                "includes_controller": 1,
                "includes_games": False,
            },
            {
                "name": "PlayStation 5 Bundle (2 Controllers + Games)",
                "console_type": ConsoleType.PS5,
                "description": "PS5 with 2 DualSense controllers and 3 games included.",
                "condition": ConsoleCondition.EXCELLENT,
                "serial_number": "PS5-BDL-001",
                "daily_rate": Decimal("399.00"),
                "weekly_rate": Decimal("2499.00"),
                "monthly_rate": Decimal("7999.00"),
                "security_deposit": Decimal("7000.00"),
                "includes_controller": 2,
                "includes_games": True,
            },
            {
                "name": "PlayStation 4 Pro",
                "console_type": ConsoleType.PS4_PRO,
                "description": "PS4 Pro 1TB. Great for 4K gaming on a budget.",
                "condition": ConsoleCondition.GOOD,
                "serial_number": "PS4-PRO-001",
                "daily_rate": Decimal("149.00"),
                "weekly_rate": Decimal("899.00"),
                "monthly_rate": Decimal("2999.00"),
                "security_deposit": Decimal("3000.00"),
                "includes_controller": 1,
                "includes_games": False,
            },
            {
                "name": "PlayStation 4 Slim",
                "console_type": ConsoleType.PS4,
                "description": "PS4 Slim 500GB. Perfect entry-level console.",
                "condition": ConsoleCondition.GOOD,
                "serial_number": "PS4-SLM-001",
                "daily_rate": Decimal("99.00"),
                "weekly_rate": Decimal("599.00"),
                "monthly_rate": Decimal("1999.00"),
                "security_deposit": Decimal("2000.00"),
                "includes_controller": 1,
                "includes_games": False,
            },
        ]

        created_count = 0
        for data in consoles:
            slug = slugify(data["name"])
            _, created = Console.objects.get_or_create(
                serial_number=data["serial_number"],
                defaults={**data, "slug": slug},
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Successfully seeded {created_count} consoles.")
        )
