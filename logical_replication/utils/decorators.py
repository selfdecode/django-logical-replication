from __future__ import annotations

from django.db.models import Model


def system_model(model_class: type[Model]) -> type[Model]:
    """Use as decorator on model
    ```
    @system_model
    class Report
    ```
    """
    model_class._meta.system_model = True  # type: ignore[attr-defined]
    return model_class


def delete_model(model_class: type[Model]) -> type[Model]:
    """Use as decorator on model. Will propgate on_delete logic to slave env.
    ```
    @delete_model
    class Report
    ```
    """
    model_class = system_model(model_class)
    model_class._meta.delete_model = True  # type: ignore[attr-defined]
    return model_class


def denormalize_model(model_class: type[Model]) -> type[Model]:
    """Use as decorator on model. Will denormalize on save/delete in slave env.
    ```
    @denormalize_model
    class Report
    ```
    """
    model_class = delete_model(model_class)
    model_class._meta.denormalize_model = True  # type: ignore[attr-defined]
    return model_class
