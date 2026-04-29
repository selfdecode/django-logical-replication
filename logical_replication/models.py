from __future__ import annotations

import logging
from uuid import uuid4

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Model, options

from logical_replication.utils import delete_model

# register as valid Meta attributes
options.DEFAULT_NAMES = options.DEFAULT_NAMES + (
    "delete_model",
    "system_model",
    "denormalize_model",
)


class ReplicatedQueue(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid4)
    object_pk = models.CharField(max_length=256)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def resolve_object(self) -> Model | None:
        try:
            return self.content_type.get_object_for_this_type(
                using=self._state.db, pk=self.object_pk
            )
        except ObjectDoesNotExist:
            logging.info(f"No matching obj for {self}")
        return None

    def process_object(self) -> None:
        raise NotImplementedError()

    def __str__(self) -> str:
        class_name = self.__class__.__name__
        return f"<{class_name}: {self.content_type.model}, pk: {self.object_pk}>"

    class Meta:
        abstract = True
        ordering = ["-created_at"]


@delete_model
class DeleteQueue(ReplicatedQueue):
    """Queue to handle deletes on slave envs"""

    def process_object(self) -> None:
        if obj := self.resolve_object():
            obj.delete()

    class Meta(ReplicatedQueue.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["content_type_id", "object_pk"],
                name="delete_unique_obj",
            )
        ]


@delete_model
class DenormalizeQueue(ReplicatedQueue):
    """Queue to handle denormalization on slave envs"""

    def process_object(self) -> None:
        if obj := self.resolve_object():
            obj.save()
