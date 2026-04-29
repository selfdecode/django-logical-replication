from django.apps import AppConfig


class DummyAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dummy_app"

    def ready(self) -> None:
        # pylint: disable=import-outside-toplevel

        # ruff: noqa: F401
        import dummy_app.signals  # pylint: disable=unused-import
