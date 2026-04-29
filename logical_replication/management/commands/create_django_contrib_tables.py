# pylint: disable=line-too-long
import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connections

from logical_replication.utils import add_custom_db_args


class Command(BaseCommand):
    help = "Create django contrib tables. Will do nothing if already exists"

    def add_arguments(self, parser):
        add_custom_db_args(parser)

    def handle(self, *args, **kwargs):
        db_ = kwargs.get("db") or "default"
        if settings.IS_MASTER_ENV and not kwargs.get("override_env"):
            raise CommandError("Can only create subs on slave env")

        with connections[db_].cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT FROM
                        pg_tables
                    WHERE
                        schemaname = 'public' AND
                        tablename  = 'django_content_type'
                    );
                """
            )
            if cursor.fetchone()[0]:
                logging.info("django content table already exists")
                logging.info("Exiting...")
                return

            with open(
                settings.BASE_DIR / "build_synced_contrib_tables.sql",
                encoding="utf8",
            ) as sql_file:
                statements = sql_file.read()
                cursor.execute(statements)

        logging.info("Django contrib table successfully created.")
        logging.info("Ok.")
