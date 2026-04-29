# pylint: disable=line-too-long
import logging
import os
from pathlib import Path

from psycopg import sql

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "657m3afea)!gdr6jvkb=q+hdb06s-54"  # nosec
REPLICATION_CONNECTION_SECRET = "dummy"  # nosec
REPLICATION_CONNECTION_SECRET_REGION = "us-east-1"  # nosec

PROJECT_SLUG = "django_logical_replication"

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_cron",
    "dummy_app.apps.DummyAppConfig",
    "logical_replication.apps.LogicalReplicationConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "sample_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "sample_project.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": PROJECT_SLUG.replace("-", "_"),
        "USER": PROJECT_SLUG.replace("-", "_"),
        "PASSWORD": "password",  # nosec B105 - test credentials only
        "HOST": "master",
        "PORT": "5432",
    },
    "slave": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": PROJECT_SLUG.replace("-", "_"),
        "USER": PROJECT_SLUG.replace("-", "_"),
        "PASSWORD": "password",  # nosec B105 - test credentials only
        "HOST": "slave",
        "PORT": "5432",
    },
}
DATABASE_ROUTERS = ["logical_replication.router.LogicalReplicationRouter"]

IS_MASTER_ENV = "slave" not in str(DATABASES["default"]["NAME"])

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Logging
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(level=LOG_LEVEL)

logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

CRON_CLASSES = [
    "logical_replication.cron.ProcessDeleteQueue",
    "logical_replication.cron.ProcessDenormalizeQueue",
]

ADDITIONAL_SYSTEM_MODELS = ["dummy_app.Outcome_categories"]
ADDITIONAL_PUBLICATION_SETTINGS = {
    "dummy_app.Outcome": sql.SQL("WHERE ({col_name} != 'test')").format(
        col_name=sql.Identifier("name")
    )
}
