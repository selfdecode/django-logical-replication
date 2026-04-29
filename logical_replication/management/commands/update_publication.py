import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from psycopg.sql import SQL, Identifier

from logical_replication.utils import (
    add_custom_db_args,
    build_full_sync_tables_sql,
    build_upsert_sync_tables_sql,
    get_delete_models,
    get_denormalize_models,
    get_full_sync_models,
    get_publication_name,
    get_upsert_only_publication_name,
    get_user_models,
    log_and_execute,
)


class Command(BaseCommand):
    help = "Update Logical Replication Publications"

    def add_arguments(self, parser):
        add_custom_db_args(parser)

        parser.add_argument(
            "--dry_run",
            dest="dry_run",
            action="store_true",
            help="Only print sql w/o running it",
        )

    def handle(self, *args, **kwargs):
        db_ = kwargs.get("db") or "default"
        if not settings.IS_MASTER_ENV and not kwargs.get("override_env"):
            raise CommandError("Can only create pub on master env")

        base_sql = SQL("ALTER PUBLICATION {pub} SET TABLE {tables};")
        pub_stmt = base_sql.format(
            pub=Identifier(get_publication_name()),
            tables=build_full_sync_tables_sql(),
        )
        pub_upsert_stmt = base_sql.format(
            pub=Identifier(get_upsert_only_publication_name()),
            tables=build_upsert_sync_tables_sql(),
        )

        if kwargs.get("dry_run"):
            with connections[db_].cursor() as cursor:
                logging.info("Printing sql to run")
                logging.info(pub_stmt.as_string(cursor.connection))
                logging.info(pub_upsert_stmt.as_string(cursor.connection))
                logging.info(
                    f"Denormalize models: {','.join(map(str, get_denormalize_models()))}"
                )
                logging.info(f"User models: {','.join(map(str, get_user_models()))}")

            return

        logging.info("Altering full publication + upsert only publication...")
        with connections[db_].cursor() as cursor:
            if get_full_sync_models():
                log_and_execute(cursor, pub_stmt)
            if get_delete_models():
                log_and_execute(cursor, pub_upsert_stmt)

        logging.info("Publications successfully updated.")
        logging.info("Ok.")
