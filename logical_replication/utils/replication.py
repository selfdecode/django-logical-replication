# pylint: disable=line-too-long
from __future__ import annotations

from typing import Any

from django.apps import apps
from django.conf import settings
from django.db.models import Model
from django.db.models.fields.related import ManyToManyField
from django.db.models.fields.reverse_related import ManyToManyRel
from psycopg import sql


def is_synced_contrib_app(app_label: str) -> bool:
    return app_label.lower() in ("contenttypes", "auth")


def get_model_meta_attr(model_class: type[Model], attr: str, default: Any) -> Any:
    return getattr(model_class._meta, attr, default)


def should_skip_validation(model_class: type[Model]) -> bool:
    skip_models = {
        apps.get_model(model_str)
        for model_str in getattr(settings, "SKIP_VALIDATION_MODELS", [])
    }
    return model_class in skip_models


def is_registered_in_settings(model_type: str, model_class: type[Model]) -> bool:
    registered_models = {
        apps.get_model(model_str)
        for model_str in getattr(
            settings, f"ADDITIONAL_{model_type.upper()}_MODELS", []
        )
    }
    return model_class in registered_models


def get_additional_publication_settings(model_class: type[Model]) -> sql.SQL | None:
    additional_settings = {
        apps.get_model(model_str): additional_setting
        for model_str, additional_setting in getattr(
            settings, "ADDITIONAL_PUBLICATION_SETTINGS", {}
        ).items()
    }

    return additional_settings.get(model_class)


def is_system_model(model_class: type[Model]) -> bool:
    if is_synced_contrib_app(model_class._meta.app_label):
        return True

    # explicitly marked
    if get_model_meta_attr(model_class, "system_model", False):
        return True

    return any(
        is_registered_in_settings(model_type, model_class)
        for model_type in ("system", "delete", "denormalize")
    )


def is_user_model(model_class: type[Model]) -> bool:
    return not is_system_model(model_class)


def is_denormalize_model(model_class: type[Model]) -> bool:
    if get_model_meta_attr(model_class, "denormalize_model", False):
        return True

    return is_registered_in_settings("denormalize", model_class)


def is_delete_model(model_class: type[Model]) -> bool:
    # denormalized models are also delete
    if is_denormalize_model(model_class):
        return True

    # explicitly marked
    if get_model_meta_attr(model_class, "delete_model", False):
        return True

    if is_registered_in_settings("delete", model_class):
        return True

    # user FK to table (on_delete)
    user_table = does_user_table_depend_on(model_class)
    if not user_table:
        return False

    if is_synced_contrib_app(model_class._meta.app_label):
        return True

    raise ValueError(
        f"{user_table=} has FK to system model {model_class}. "
        "Please mark explicitly as @delete_model "
        "or register in settings.py"
    )


def does_user_table_depend_on(model_class: type[Model]) -> type[Model] | None:
    # reverse OneToOne + ForeignKey (many2many has no on_delete)
    def is_reverse_one2one_or_fk_user_model(field: Any) -> bool:
        return (
            field.related_model
            and is_user_model(field.related_model)
            and field.auto_created
            and not isinstance(field, ManyToManyRel)
        )

    for field in model_class._meta.get_fields():
        if is_reverse_one2one_or_fk_user_model(field):
            return field.related_model  # type: ignore[return-value]
    return None


def is_forward_one2one_or_fk(field: Any) -> bool:
    # forward OneToOne + ForeignKey (many2many has no on_delete)
    return (
        field.related_model
        and not field.auto_created
        and not isinstance(field, ManyToManyField)
    )


def validate_no_system_to_user_dep(model_class: type[Model]) -> bool:
    if should_skip_validation(model_class):
        return True

    for field in model_class._meta.get_fields():
        if is_forward_one2one_or_fk(field) and is_user_model(field.related_model):  # type: ignore[arg-type]
            raise ValueError(
                f"System model {model_class} has FK or one2one"
                f" to user model: {field.related_model}"
            )
    return True


def get_system_models() -> list[type[Model]]:
    return [
        model
        for model in apps.get_models(include_auto_created=True)
        if is_system_model(model) and validate_no_system_to_user_dep(model)
    ]


def get_user_models() -> list[type[Model]]:
    return [
        model
        for model in apps.get_models(include_auto_created=True)
        if not is_system_model(model)
    ]


def get_denormalize_models() -> list[type[Model]]:
    return [model for model in get_system_models() if is_denormalize_model(model)]


def get_delete_models() -> list[type[Model]]:
    return [model for model in get_system_models() if is_delete_model(model)]


def get_full_sync_models() -> list[type[Model]]:
    delete_models = set(get_delete_models())
    return [model for model in get_system_models() if model not in delete_models]
