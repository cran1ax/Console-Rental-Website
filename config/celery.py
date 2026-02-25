"""
Celery application for Corner Console.

Start the worker::

    celery -A config worker -l info

Start the beat scheduler (periodic tasks)::

    celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

Or run both in a single process (dev only)::

    celery -A config worker -B -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
"""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("corner_console")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


# ─── Periodic Task Schedule ──────────────────────────────────────
# These are the *default* entries.  django-celery-beat's
# DatabaseScheduler merges them with any schedules you manage
# through the Django admin.
# ─────────────────────────────────────────────────────────────────
app.conf.beat_schedule = {
    # 1) Email reminders — every day at 9:00 AM
    "send-rental-end-reminders": {
        "task": "apps.rentals.tasks.send_rental_end_reminders",
        "schedule": crontab(hour=9, minute=0),
        "options": {"queue": "default"},
    },
    # 2) Auto-mark late rentals — every day at midnight
    "auto-mark-late-rentals": {
        "task": "apps.rentals.tasks.auto_mark_late_rentals",
        "schedule": crontab(hour=0, minute=5),
        "options": {"queue": "default"},
    },
    # 3) Auto-refund deposits — every day at 10:00 AM
    "auto-refund-deposits": {
        "task": "apps.rentals.tasks.auto_refund_deposits",
        "schedule": crontab(hour=10, minute=0),
        "options": {"queue": "default"},
    },
    # 4) Expire stale Stripe checkout sessions — every 30 minutes
    "expire-stale-checkout-sessions": {
        "task": "apps.payments.tasks.expire_stale_checkout_sessions",
        "schedule": crontab(minute="*/30"),
        "options": {"queue": "default"},
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f"Request: {self.request!r}")
