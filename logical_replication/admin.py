# pylint: disable=import-outside-toplevel
from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.db.models import Model
from django.http import HttpRequest
from django.urls import reverse
from django.utils.html import format_html

from logical_replication.models import DeleteQueue, DenormalizeQueue, ReplicatedQueue
from logical_replication.utils import is_system_model

if TYPE_CHECKING:
    from collections.abc import Callable


class SystemModelAdminMixin:
    """Prevents creating/updating on if slave env"""

    def has_add_permission(self, request: HttpRequest) -> bool:
        if not settings.IS_MASTER_ENV:
            return False

        return super().has_add_permission(request)  # type: ignore[misc]

    def has_change_permission(
        self, request: HttpRequest, obj: Model | None = None
    ) -> bool:
        if not settings.IS_MASTER_ENV:
            return False

        return super().has_change_permission(request, obj=obj)  # type: ignore[misc]


class ReplicatedQueueAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "content_type",
        "resolved_obj_pk",
        "created_at",
        "updated_at",
    ]
    search_fields = ["id", "content_type__id", "object_pk"]

    @staticmethod
    def resolved_obj_pk(obj: ReplicatedQueue) -> str:
        try:
            resolved_obj = obj.resolve_object()
            if resolved_obj is None:
                return obj.object_pk
            model_class = type(resolved_obj)
            url = reverse(
                f"admin:{model_class._meta.app_label}_"
                f"{model_class._meta.model_name}_change",
                args=(resolved_obj.pk,),
            )
            return format_html("<a href='{}'>{}</a>", url, resolved_obj.pk)
        except Exception:  # pylint: disable=broad-exception-caught
            return obj.object_pk


@admin.register(DeleteQueue)
class DeleteQueueAdmin(ReplicatedQueueAdmin):
    pass


@admin.register(DenormalizeQueue)
class DenormalizeQueueAdmin(ReplicatedQueueAdmin):
    pass


def admin_register(
    *models: type[Model], site: AdminSite | None = None
) -> Callable[[type[ModelAdmin]], type[ModelAdmin]]:
    """Registers models with django admin, adding SystemModelMixin for system models"""

    from django.contrib.admin.sites import site as default_site

    def _model_admin_wrapper(admin_class: type[ModelAdmin]) -> type[ModelAdmin]:
        if not models:
            raise ValueError("At least one model must be passed to register.")

        admin_site = site or default_site

        if not isinstance(admin_site, AdminSite):
            raise ValueError("site must subclass AdminSite")

        if not issubclass(admin_class, ModelAdmin):
            raise ValueError("Wrapped class must subclass ModelAdmin.")

        if is_system_model(models[0]):
            system_admin_class: type[ModelAdmin] = type(
                f"System{admin_class.__name__}",
                (SystemModelAdminMixin, admin_class),
                {},
            )
        else:
            system_admin_class = admin_class

        admin_site.register(models, admin_class=system_admin_class)

        return system_admin_class

    return _model_admin_wrapper


def register_replicated_user_admin(
    site: AdminSite = admin.site,
    admin_class: type[UserAdmin] = UserAdmin,
    user_model: type[Model] | None = None,
) -> None:
    """Add SystemModelMixin to user model admin. Call in any app's admin.py"""

    if user_model is None:
        user_model = get_user_model()

    site.unregister(user_model)
    admin_register(user_model)(admin_class)
