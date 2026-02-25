"""
Production settings for Corner Console project.

Checklist before deploying:
    1. Set DJANGO_SETTINGS_MODULE=config.settings.prod in your .env
    2. Generate a strong DJANGO_SECRET_KEY
    3. Configure DJANGO_ALLOWED_HOSTS with your domain(s)
    4. Set CSRF_TRUSTED_ORIGINS to https://yourdomain.com
    5. Ensure DATABASE_URL points to your production Postgres
    6. Configure Stripe *live* keys (not test)
    7. Provision SMTP credentials or a transactional email service
    8. (Optional) set up S3 for media files
    9. (Optional) set SENTRY_DSN for error tracking
"""

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from .base import *  # noqa: F401, F403
from .base import MIDDLEWARE, env

# ════════════════════════════════════════════════════════════════════
# CORE
# ════════════════════════════════════════════════════════════════════
DEBUG = False
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

# ════════════════════════════════════════════════════════════════════
# SECURITY — HTTPS / HSTS / CSRF / Cookies
# ════════════════════════════════════════════════════════════════════
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# HSTS — tell browsers to *only* use HTTPS for the next year.
SECURE_HSTS_SECONDS = 31_536_000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookies — HTTPS only
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # 14 days

# Content security
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# CSRF trusted origins — MUST include the production domain(s).
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# ════════════════════════════════════════════════════════════════════
# DATABASE — Connection pooling
# ════════════════════════════════════════════════════════════════════
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=600)  # noqa: F405
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True  # noqa: F405
DATABASES["default"]["OPTIONS"] = {  # noqa: F405
    "connect_timeout": 10,
    "options": "-c statement_timeout=30000",  # 30 s query timeout
}

# ════════════════════════════════════════════════════════════════════
# STATIC FILES — WhiteNoise (served from the app itself)
# ════════════════════════════════════════════════════════════════════
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# ════════════════════════════════════════════════════════════════════
# MEDIA FILES — AWS S3 (optional)
# ════════════════════════════════════════════════════════════════════
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="ap-south-1")
AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
AWS_DEFAULT_ACL = "public-read"
AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
AWS_QUERYSTRING_AUTH = False
AWS_S3_FILE_OVERWRITE = False

if AWS_STORAGE_BUCKET_NAME:
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    }

# ════════════════════════════════════════════════════════════════════
# CACHING — Redis
# ════════════════════════════════════════════════════════════════════
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://redis:6379/2"),
        "TIMEOUT": 60 * 15,  # 15 min default
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,  # degrade gracefully
        },
    },
}
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# ════════════════════════════════════════════════════════════════════
# EMAIL — Production SMTP
# ════════════════════════════════════════════════════════════════════
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# ════════════════════════════════════════════════════════════════════
# SENTRY — Error tracking
# ════════════════════════════════════════════════════════════════════
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.1),
        profiles_sample_rate=env.float("SENTRY_PROFILES_SAMPLE_RATE", default=0.1),
        send_default_pii=False,  # GDPR-safe default
        environment="production",
    )

# ════════════════════════════════════════════════════════════════════
# LOGGING — JSON-structured, production-grade
# ════════════════════════════════════════════════════════════════════
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": (
                "[{asctime}] {levelname} {name} {module}.{funcName}:{lineno} "
                "pid={process:d} tid={thread:d} — {message}"
            ),
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/app/logs/django.log",
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console", "file"],
            "level": "WARNING",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# ════════════════════════════════════════════════════════════════════
# ADMIN
# ════════════════════════════════════════════════════════════════════
ADMIN_URL = env("DJANGO_ADMIN_URL", default="admin/")

