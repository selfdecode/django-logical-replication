# pylint: disable=import-outside-toplevel
from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_delete, post_save


class LogicalReplicationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "logical_replication"

    def ready(self) -> None:
        from .event_handlers import add_to_delete_queue, add_to_denormalize_queue
        from .utils import get_delete_models, get_denormalize_models

        if getattr(settings, "DISABLE_LOGICAL_REPLICATION_SIGNALS", False):
            return super().ready()

        # denormalize model post_save
        for model in get_denormalize_models():
            post_save.connect(add_to_denormalize_queue, model)

        # delete queue signals
        for model in get_delete_models():
            post_delete.connect(add_to_delete_queue, model)

        return super().ready()
