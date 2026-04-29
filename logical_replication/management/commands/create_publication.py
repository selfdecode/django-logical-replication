import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from psycopg.sql import SQL, Identifier, Literal

from logical_replication.utils import (
    add_custom_db_args,
    get_publication_name,
    get_subscription_name,
    get_upsert_only_publication_name,
    get_upsert_only_subscription_name,
    log_and_execute,
)


class Command(BaseCommand):
    help = "Create Logical Replication Initial Empty Publications"

    def add_arguments(self, parser):
        parser.add_argument(
            "--setup_sync",
            dest="setup_sync",
            action="store_true",
            help="Setup config to support sync",
        )

        add_custom_db_args(parser)

    def handle(self, *args, **kwargs):
        db_ = kwargs.get("db") or "default"
        if not settings.IS_MASTER_ENV and not kwargs.get("override_env"):
            raise CommandError("Can only create pub on master env")

        base_sql = SQL("CREATE PUBLICATION {pub};")
        create_pub_stmt = base_sql.format(pub=Identifier(get_publication_name()))

        base_upsert_sql = SQL(
            "CREATE PUBLICATION {pub} WITH (publish = 'insert, update');"
        )
        create_upsert_pub_stmt = base_upsert_sql.format(
            pub=Identifier(get_upsert_only_publication_name())
        )

        logging.info("Creating full publication + upsert only publication...")
        with connections[db_].cursor() as cursor:
            log_and_execute(cursor, create_pub_stmt)
            log_and_execute(cursor, create_upsert_pub_stmt)

            if kwargs.get("setup_sync"):
                self.setup_sync(cursor)

        logging.info("Publications successfully created.")
        logging.info("Ok.")

    @staticmethod
    def setup_sync(cursor):
        sub_name = get_subscription_name()
        upsert_sub_name = get_upsert_only_subscription_name()
        sync_sql = SQL("ALTER SYSTEM SET synchronous_standby_names TO {sub_names};")
        sync_stmt = sync_sql.format(sub_names=Literal(f"{sub_name}, {upsert_sub_name}"))
        reload_conf_stmt = "SELECT pg_reload_conf();"

        log_and_execute(cursor, sync_stmt)
        log_and_execute(cursor, reload_conf_stmt)
