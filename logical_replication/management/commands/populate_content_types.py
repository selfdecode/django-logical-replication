from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Force populate (lazy) content type instances"

    def handle(self, *_args, **_kwargs):
        if not settings.IS_MASTER_ENV:
            return

        content_types = ContentType.objects.all()
        lookup = {(ct.app_label, ct.model): ct for ct in content_types}

        for model in apps.get_models(include_auto_created=True):
            if not lookup.get((model._meta.app_label, model._meta.model_name)):
                ContentType.objects.create(
                    app_label=model._meta.app_label,
                    model=model._meta.model_name,
                )
