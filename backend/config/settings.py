"""
Django settings for the Claims Register API.

Everything environment-specific comes from environment variables (see
`.env.example`). The database is Postgres only: money columns are `numeric`
and totals are summed in SQL, which SQLite would silently do in floating
point. Startup fails loudly if `DATABASE_URL` is missing.
"""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


# --- Security ---------------------------------------------------------------

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key-set-SECRET_KEY-in-production")
DEBUG = env_bool("DEBUG", True)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")

# --- Applications -----------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",  # required by DRF's test client and browsable API
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "corsheaders",
    "claims.apps.ClaimsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": ["django.template.context_processors.request"]},
    },
]

# --- Database (Postgres only) -----------------------------------------------

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ImproperlyConfigured(
        "DATABASE_URL is required (Postgres). Copy .env.example to .env, or start the "
        "local database with `docker compose up -d`."
    )
if not DATABASE_URL.startswith(("postgres://", "postgresql://")):
    raise ImproperlyConfigured("DATABASE_URL must point at a PostgreSQL database.")

DATABASES = {
    "default": dj_database_url.config(default=DATABASE_URL, conn_max_age=600, conn_health_checks=True),
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Internationalisation ---------------------------------------------------

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "UTC"  # "today" for date validation is UTC; Ghana is on GMT.
USE_I18N = True
USE_TZ = True

# --- Static files (only the DRF browsable API uses these) -------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# --- CORS -------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")

# --- Django REST Framework --------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"]
    + (["rest_framework.renderers.BrowsableAPIRenderer"] if DEBUG else []),
    # Money travels as strings ("1250.00") so no client ever sees a float.
    "COERCE_DECIMAL_TO_STRING": True,
}

# --- Logging ----------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
