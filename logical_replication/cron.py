# pylint: disable=invalid-name,no-self-use
import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django_cron import CronJobBase, Schedule

from logical_replication.models import DeleteQueue, DenormalizeQueue, ReplicatedQueue


def process_queue(model_class: type[ReplicatedQueue]):
    action = "delete" if model_class is DeleteQueue else "denormalize"

    if settings.IS_MASTER_ENV:  # only slave envs process queue
        if days := getattr(settings, f"EXPIRE_{action.upper()}_QUEUE_AFTER", None):
            expiry_point = timezone.now() - timedelta(days=days)
            model_class.objects.filter(created_at__lte=expiry_point).delete()
        return

    logging.info(f"Start processing {action} queue...")
    batch_size = getattr(settings, f"{action.upper()}_BATCH_SIZE", 100)
    batch = model_class.objects.all()[:batch_size]

    logging.info(f"{len(batch)} rows to be processed.")
    for row in batch:
        try:
            row.process_object()
            row.delete()
        except Exception:
            logging.exception(
                f"Failed to process {row} (pk={row.pk}, content_type={row.content_type}, object_pk={row.object_pk})"
            )

    logging.info("Batch successfully processed.")
    logging.info("Ok.")


class ProcessDeleteQueue(CronJobBase):
    """Cron job that processes delete queue.
    Customize schedule via `DELETE_EVEY_MINS`
    And batch size via `DELETE_BATCH_SIZE` in settings"""

    schedule = Schedule(run_every_mins=getattr(settings, "DELETE_EVERY_MINS", 5))
    code = "logical_replication.cron.ProcessDeleteQueue"

    def do(self):
        process_queue(DeleteQueue)


class ProcessDenormalizeQueue(CronJobBase):
    """Cron job that processes denormalize queue.
    Customize schedule via `DENORMALIZE_EVEY_MINS`
    And batch size via `DENORMALIZE_BATCH_SIZE` in settings"""

    schedule = Schedule(run_every_mins=getattr(settings, "DENORMALIZE_EVERY_MINS", 5))
    code = "logical_replication.cron.ProcessDenormalizeQueue"

    def do(self):
        process_queue(DenormalizeQueue)
