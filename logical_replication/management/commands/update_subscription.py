import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from psycopg.sql import SQL, Identifier

from logical_replication.utils import (
    add_custom_db_args,
    get_subscription_name,
    get_upsert_only_subscription_name,
    log_and_execute,
)


class Command(BaseCommand):
    help = "Update Logical Replication Initial Subscriptions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dont_copy_data",
            dest="dont_copy_data",
            action="store_true",
            help="Whether to copy pre-existing data in the publications"
            "Note - previously subscribed tables are *not* copied",
        )

        parser.add_argument(
            "--setup_sync",
            dest="setup_sync",
            action="store_true",
            help="Setup config to support sync",
        )

        add_custom_db_args(parser)

    def handle(self, *args, **kwargs):
        db_ = kwargs.get("db") or "default"
        if settings.IS_MASTER_ENV and not kwargs.get("override_env"):
            raise CommandError("Can only create subs on slave env")

        base_stmt = "ALTER SUBSCRIPTION {sub} REFRESH PUBLICATION"

        options = []
        if kwargs.get("dont_copy_data"):
            options.append("copy_data = false")
        if kwargs.get("setup_sync"):
            options.append("synchronous_commit = 'on'")
        if options:
            base_stmt = f"{base_stmt} WITH ({', '.join(options)});"
        else:
            base_stmt = f"{base_stmt};"

        sub_stmt = SQL(base_stmt).format(sub=Identifier(get_subscription_name()))
        sub_upsert_stmt = SQL(base_stmt).format(
            sub=Identifier(get_upsert_only_subscription_name())
        )

        logging.info("Updating full subscription + upsert only subscription...")
        with connections[db_].cursor() as cursor:
            log_and_execute(cursor, sub_stmt)
            log_and_execute(cursor, sub_upsert_stmt)

        logging.info("Subscriptions successfully updated.")
        logging.info("Ok.")
