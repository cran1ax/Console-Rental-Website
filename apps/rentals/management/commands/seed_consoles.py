from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.rentals.models import (
    Accessory,
    AccessoryCategory,
    ConditionStatus,
    Console,
    ConsoleType,
    Game,
    Genre,
    Platform,
)


class Command(BaseCommand):
    help = "Seed database with sample consoles, games, and accessories"

    @transaction.atomic
    def handle(self, *args, **options):
        consoles_created = self._seed_consoles()
        games_created = self._seed_games()
        accessories_created = self._seed_accessories()

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded: {consoles_created} consoles, "
                f"{games_created} games, {accessories_created} accessories."
            )
        )

    # ------------------------------------------------------------------
    # Consoles
    # ------------------------------------------------------------------
    def _seed_consoles(self):
        consoles = [
            {
                "name": "PlayStation 5 Standard",
                "console_type": ConsoleType.PS5,
                "description": "Latest PS5 with disc drive. Includes 1 DualSense controller.",
                "condition_status": ConditionStatus.EXCELLENT,
                "daily_price": Decimal("299.00"),
                "weekly_price": Decimal("1799.00"),
                "monthly_price": Decimal("5999.00"),
                "security_deposit": Decimal("5000.00"),
                "stock_quantity": 5,
                "available_quantity": 5,
            },
            {
                "name": "PlayStation 5 Digital Edition",
                "console_type": ConsoleType.PS5_DIGITAL,
                "description": "PS5 Digital Edition — no disc drive. 1 DualSense controller.",
                "condition_status": ConditionStatus.EXCELLENT,
                "daily_price": Decimal("249.00"),
                "weekly_price": Decimal("1499.00"),
                "monthly_price": Decimal("4999.00"),
                "security_deposit": Decimal("4000.00"),
                "stock_quantity": 4,
                "available_quantity": 4,
            },
            {
                "name": "PlayStation 5 Pro",
                "console_type": ConsoleType.PS5_PRO,
                "description": "PS5 Pro with enhanced GPU for 8K output. 1 DualSense controller.",
                "condition_status": ConditionStatus.EXCELLENT,
                "daily_price": Decimal("399.00"),
                "weekly_price": Decimal("2499.00"),
                "monthly_price": Decimal("7999.00"),
                "security_deposit": Decimal("7000.00"),
                "stock_quantity": 3,
                "available_quantity": 3,
            },
            {
                "name": "PlayStation 4 Pro",
                "console_type": ConsoleType.PS4_PRO,
                "description": "PS4 Pro 1TB — great for 4K gaming on a budget.",
                "condition_status": ConditionStatus.GOOD,
                "daily_price": Decimal("149.00"),
                "weekly_price": Decimal("899.00"),
                "monthly_price": Decimal("2999.00"),
                "security_deposit": Decimal("3000.00"),
                "stock_quantity": 6,
                "available_quantity": 6,
            },
            {
                "name": "PlayStation 4 Slim",
                "console_type": ConsoleType.PS4_SLIM,
                "description": "PS4 Slim 500GB — perfect entry-level console.",
                "condition_status": ConditionStatus.GOOD,
                "daily_price": Decimal("99.00"),
                "weekly_price": Decimal("599.00"),
                "monthly_price": Decimal("1999.00"),
                "security_deposit": Decimal("2000.00"),
                "stock_quantity": 8,
                "available_quantity": 8,
            },
        ]

        created = 0
        for data in consoles:
            data["slug"] = slugify(data["name"])
            _, is_new = Console.objects.get_or_create(
                slug=data["slug"],
                defaults=data,
            )
            if is_new:
                created += 1
        return created

    # ------------------------------------------------------------------
    # Games
    # ------------------------------------------------------------------
    def _seed_games(self):
        games = [
            {
                "title": "God of War Ragnarök",
                "platform": Platform.PS5,
                "genre": Genre.ACTION,
                "description": "Embark on an epic journey with Kratos and Atreus.",
                "rating": Decimal("9.5"),
                "daily_price": Decimal("49.00"),
                "stock_quantity": 10,
                "available_quantity": 10,
            },
            {
                "title": "Spider-Man 2",
                "platform": Platform.PS5,
                "genre": Genre.ACTION,
                "description": "Swing through Marvel's New York as Peter and Miles.",
                "rating": Decimal("9.2"),
                "daily_price": Decimal("49.00"),
                "stock_quantity": 10,
                "available_quantity": 10,
            },
            {
                "title": "Horizon Forbidden West",
                "platform": Platform.CROSS_GEN,
                "genre": Genre.RPG,
                "description": "Explore the Forbidden West as Aloy.",
                "rating": Decimal("8.8"),
                "daily_price": Decimal("39.00"),
                "stock_quantity": 8,
                "available_quantity": 8,
            },
            {
                "title": "Gran Turismo 7",
                "platform": Platform.CROSS_GEN,
                "genre": Genre.RACING,
                "description": "The real driving simulator returns.",
                "rating": Decimal("8.7"),
                "daily_price": Decimal("39.00"),
                "stock_quantity": 8,
                "available_quantity": 8,
            },
            {
                "title": "The Last of Us Part II Remastered",
                "platform": Platform.PS5,
                "genre": Genre.ACTION,
                "description": "Remastered version with haptic feedback and 4K.",
                "rating": Decimal("9.3"),
                "daily_price": Decimal("49.00"),
                "stock_quantity": 7,
                "available_quantity": 7,
            },
            {
                "title": "FIFA 24 (EA Sports FC 24)",
                "platform": Platform.CROSS_GEN,
                "genre": Genre.SPORTS,
                "description": "The world's game, reimagined.",
                "rating": Decimal("7.5"),
                "daily_price": Decimal("29.00"),
                "stock_quantity": 12,
                "available_quantity": 12,
            },
            {
                "title": "Uncharted 4: A Thief's End",
                "platform": Platform.PS4,
                "genre": Genre.ACTION,
                "description": "Nathan Drake's greatest adventure.",
                "rating": Decimal("9.0"),
                "daily_price": Decimal("29.00"),
                "stock_quantity": 10,
                "available_quantity": 10,
            },
            {
                "title": "Demon's Souls",
                "platform": Platform.PS5,
                "genre": Genre.RPG,
                "description": "A stunning PS5 remake of the cult classic.",
                "rating": Decimal("9.0"),
                "daily_price": Decimal("49.00"),
                "stock_quantity": 6,
                "available_quantity": 6,
            },
        ]

        created = 0
        for data in games:
            data["slug"] = slugify(data["title"])
            _, is_new = Game.objects.get_or_create(
                slug=data["slug"],
                defaults=data,
            )
            if is_new:
                created += 1
        return created

    # ------------------------------------------------------------------
    # Accessories
    # ------------------------------------------------------------------
    def _seed_accessories(self):
        accessories = [
            {
                "name": "DualSense Wireless Controller (Extra)",
                "category": AccessoryCategory.CONTROLLER,
                "compatible_with": Platform.PS5,
                "description": "Extra DualSense controller with haptic feedback.",
                "price_per_day": Decimal("29.00"),
                "stock_quantity": 15,
                "available_quantity": 15,
            },
            {
                "name": "DualShock 4 Controller (Extra)",
                "category": AccessoryCategory.CONTROLLER,
                "compatible_with": Platform.PS4,
                "description": "Extra DualShock 4 wireless controller.",
                "price_per_day": Decimal("19.00"),
                "stock_quantity": 12,
                "available_quantity": 12,
            },
            {
                "name": "PlayStation VR2",
                "category": AccessoryCategory.VR_HEADSET,
                "compatible_with": Platform.PS5,
                "description": "Next-gen VR headset with OLED displays.",
                "price_per_day": Decimal("99.00"),
                "stock_quantity": 4,
                "available_quantity": 4,
            },
            {
                "name": "Pulse 3D Wireless Headset",
                "category": AccessoryCategory.HEADSET,
                "compatible_with": Platform.PS5,
                "description": "3D Audio-enabled wireless headset for PS5.",
                "price_per_day": Decimal("19.00"),
                "stock_quantity": 10,
                "available_quantity": 10,
            },
            {
                "name": "HD Camera",
                "category": AccessoryCategory.CAMERA,
                "compatible_with": Platform.PS5,
                "description": "1080p HD camera for streaming and video chat.",
                "price_per_day": Decimal("9.00"),
                "stock_quantity": 6,
                "available_quantity": 6,
            },
            {
                "name": "DualSense Charging Station",
                "category": AccessoryCategory.CHARGING_DOCK,
                "compatible_with": Platform.PS5,
                "description": "Charge two DualSense controllers simultaneously.",
                "price_per_day": Decimal("9.00"),
                "stock_quantity": 8,
                "available_quantity": 8,
            },
            {
                "name": "HDMI 2.1 Cable (3m)",
                "category": AccessoryCategory.CABLE,
                "compatible_with": Platform.CROSS_GEN,
                "description": "Ultra High Speed HDMI cable for 4K 120Hz.",
                "price_per_day": Decimal("5.00"),
                "stock_quantity": 20,
                "available_quantity": 20,
            },
        ]

        created = 0
        for data in accessories:
            data["slug"] = slugify(data["name"])
            _, is_new = Accessory.objects.get_or_create(
                slug=data["slug"],
                defaults=data,
            )
            if is_new:
                created += 1
        return created
