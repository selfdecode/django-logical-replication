from __future__ import annotations

from typing import Any

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Model

from logical_replication.models import DeleteQueue, DenormalizeQueue, ReplicatedQueue


def add_to_queue(model_class: type[ReplicatedQueue], instance: Model) -> None:
    if not settings.IS_MASTER_ENV or issubclass(type(instance), ReplicatedQueue):
        return

    model_class.objects.create(
        content_type=ContentType.objects.get_for_model(instance),
        object_pk=instance.pk,
    )


def add_to_delete_queue(instance: Model, *args: Any, **kwargs: Any) -> None:
    add_to_queue(DeleteQueue, instance)


def add_to_denormalize_queue(instance: Model, *args: Any, **kwargs: Any) -> None:
    add_to_queue(DenormalizeQueue, instance)
