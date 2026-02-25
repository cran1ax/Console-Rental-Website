"""
Test settings for Corner Console project.
"""
from .base import *  # noqa: F401, F403

# ========================
# FASTER PASSWORD HASHING FOR TESTS
# ========================
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# ========================
# IN-MEMORY DATABASE
# ========================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# ========================
# EMAIL
# ========================
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# ========================
# CELERY (synchronous in tests)
# ========================
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ========================
# CACHING
# ========================
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# ========================
# THROTTLING (disabled in tests)
# ========================
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {}  # noqa: F405
