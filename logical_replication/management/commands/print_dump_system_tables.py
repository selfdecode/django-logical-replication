import logging

from django.core.management.base import BaseCommand

from logical_replication.utils import build_dump_command


class Command(BaseCommand):
    help = "Print pg_dump command to dump all system table data"

    def handle(self, *args, **kwargs):
        logging.info(build_dump_command())
