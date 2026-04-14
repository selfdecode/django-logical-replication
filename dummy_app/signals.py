from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from dummy_app.models import Outcome


@receiver(post_save, sender=Outcome)
def denormalize_name(instance: Outcome, **_kwargs):
    instance.result_set.all().update(outcome_name=instance.name)  # type: ignore


@receiver(pre_delete, sender=Outcome)
def set_name_to_empty(instance: Outcome, **_kwargs):
    instance.result_set.all().update(outcome_name="")  # type: ignore
