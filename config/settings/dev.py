"""
Development settings for Corner Console project.
"""
from .base import *  # noqa: F401, F403
from .base import INSTALLED_APPS, MIDDLEWARE

# ========================
# DEBUG
# ========================
DEBUG = True

# ========================
# ADDITIONAL APPS
# ========================
INSTALLED_APPS += [
    "debug_toolbar",
]

MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")

# ========================
# DEBUG TOOLBAR
# ========================
INTERNAL_IPS = [
    "127.0.0.1",
    "localhost",
]

DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG,
}

# ========================
# EMAIL
# ========================
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ========================
# DRF (Add browsable API in dev)
# ========================
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]

# ========================
# CORS (Allow all in dev)
# ========================
CORS_ALLOW_ALL_ORIGINS = True

# ========================
# CACHING (local memory in dev)
# ========================
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# ========================
# LOGGING (verbose in dev)
# ========================
LOGGING["handlers"]["console"]["level"] = "DEBUG"  # noqa: F405
LOGGING["handlers"]["console"]["filters"] = []  # noqa: F405
