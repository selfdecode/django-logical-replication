# pylint: disable=line-too-long,too-many-arguments,too-many-positional-arguments
import logging

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import models
from django.db.models import Model, ProtectedError, Q, Subquery

try:
    from polymorphic.deletion import PolymorphicGuard
except ImportError:
    PolymorphicGuard = None

from logical_replication.utils import (
    add_custom_db_args,
    is_forward_one2one_or_fk,
    is_system_model,
    is_user_model,
)


def validate_models(table_names: str) -> list[type[Model]]:
    return [apps.get_model(table_name) for table_name in table_names.split(",")]


def is_polymorphic(model_class: type[Model]):
    return hasattr(model_class, "polymorphic_primary_key_name")


class Command(BaseCommand):
    help = "Resync User Table Foreign Keys"

    def add_arguments(self, parser):
        add_custom_db_args(parser)

        parser.add_argument(
            "--skip",
            dest="skip",
            type=validate_models,
            help="Comma seperated list of models e.g. reports.Report,traits.Trait",
        )

        parser.add_argument(
            "--delete_protect",
            dest="delete_protect",
            type=validate_models,
            help="Comma seperated list of models e.g. reports.Report,traits.Trait",
        )

        parser.add_argument(
            "--null_protect",
            dest="null_protect",
            type=validate_models,
            help="Comma seperated list of models e.g. reports.Report,traits.Trait",
        )

    def handle(self, *args, **kwargs):
        db_ = kwargs.get("db") or "default"
        if settings.IS_MASTER_ENV and not kwargs.get("override_env"):
            raise CommandError("Should only resync fks on slave env")

        skip_models = kwargs.get("skip") or []
        delete_protect = kwargs.get("delete_protect") or []
        null_protect = kwargs.get("null_protect") or []

        user_models = [
            model
            for model in apps.get_models(include_auto_created=True)
            if is_user_model(model) and model not in skip_models
        ]

        for model in user_models:
            for field in self.get_linked_system_model_fields(model):
                logging.info(f"Handling {model}'s {field}...")
                self.handle_delete(field, model, db_, delete_protect, null_protect)

        logging.info("User table FKs resynced.")
        logging.info("Ok.")

    @classmethod
    def handle_delete(cls, field, model_class, db_, delete_protect, null_protect):
        db_col = field.get_attname_column()[1]
        target_db_col = field.target_field.get_attname_column()[1]
        exclude_query = Q(
            **{
                f"{db_col}__in": Subquery(
                    field.related_model.objects.values_list(target_db_col)
                )
            }
        ) | Q(**{f"{db_col}__isnull": True})
        queryset = model_class.objects.using(db_).exclude(exclude_query)

        if is_polymorphic(model_class):
            queryset = queryset.non_polymorphic()  # type: ignore

        on_delete = field.remote_field.on_delete

        # Unwrap PolymorphicGuard to get the real on_delete action
        if PolymorphicGuard is not None and isinstance(on_delete, PolymorphicGuard):
            on_delete = on_delete.action

        if on_delete is models.CASCADE:
            logging.info("Cascade deleting...")
            queryset.delete()

        elif on_delete is models.SET_NULL:
            logging.info("Setting null...")
            queryset.update(**{db_col: None})

        elif on_delete is models.SET_DEFAULT:
            logging.info("Setting to default...")
            queryset.update(**{db_col: field.get_default()})

        elif on_delete is models.PROTECT:
            if model_class in delete_protect:
                logging.info("Cascade deleting (overwrite protect)...")
                cls.delete_protected(queryset)
            elif model_class in null_protect:
                logging.info("Setting null (overwrite protect)...")
                queryset.update(**{db_col: None})
            else:
                raise CommandError(
                    f"{model_class} on delete is protected."
                    "Either handle manually and skip or explicitly flag ignore_protect"
                )
        else:
            raise CommandError(f"{on_delete=} not supported. Please handle manually")

    @staticmethod
    def delete_protected(queryset):
        while True:
            try:
                queryset.delete()
                break
            except ProtectedError as error:
                for obj in error.protected_objects:
                    obj.delete()

    @staticmethod
    def get_linked_system_model_fields(model_class: type[Model]):
        return [
            field
            for field in model_class._meta.get_fields()
            if is_forward_one2one_or_fk(field) and is_system_model(field.related_model)  # type: ignore
        ]
