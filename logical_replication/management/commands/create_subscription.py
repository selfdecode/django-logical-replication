import json
import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from psycopg.sql import SQL, Identifier, Literal

from logical_replication.utils import (
    add_custom_db_args,
    db_safe_project_slug,
    get_publication_name,
    get_subscription_name,
    get_upsert_only_publication_name,
    get_upsert_only_subscription_name,
)


def get_connection_string():
    """Fetches connection values from aws secrets manager
    Using settings.REPLICATION_CONNECTION_SECRET and
    settings.REPLICATION_CONNECTION_SECRET_REGION (default=us-east-1)

    Expect keys host, user and password.

    REQUIRES boto3 be installed."""

    import boto3  # pylint: disable=import-outside-toplevel,import-error

    region_name = getattr(settings, "REPLICATION_CONNECTION_SECRET_REGION", "us-east-1")

    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)
    response = client.get_secret_value(SecretId=settings.REPLICATION_CONNECTION_SECRET)

    secret = json.loads(response["SecretString"])
    dbname = secret.get("dbname", db_safe_project_slug())
    return (
        f"dbname={dbname} host={secret['host']} "
        f"user={secret['user']} password={secret['password']}"
    )


class Command(BaseCommand):
    help = "Create Logical Replication Initial Subscriptions"

    def add_arguments(self, parser):
        add_custom_db_args(parser)

        parser.add_argument(
            "-c",
            "--connection_string",
            type=str,
            help="e.g.'dbname=reports host=localhost user=user password=password'",
        )

    def handle(self, *args, **kwargs):
        db_ = kwargs.get("db") or "default"
        if settings.IS_MASTER_ENV and not kwargs.get("override_env"):
            raise CommandError("Can only create subs on slave env")

        connection = kwargs.get("connection_string") or get_connection_string()

        base_sql = SQL("CREATE SUBSCRIPTION {sub} CONNECTION {con} PUBLICATION {pub};")
        sub_stmt = base_sql.format(
            sub=Identifier(get_subscription_name()),
            con=Literal(connection),
            pub=Identifier(get_publication_name()),
        )
        sub_upsert_stmt = base_sql.format(
            sub=Identifier(get_upsert_only_subscription_name()),
            con=Literal(connection),
            pub=Identifier(get_upsert_only_publication_name()),
        )

        logging.info("Creating full subscription + upsert only subscription...")
        with connections[db_].cursor() as cursor:
            cursor.execute(sub_stmt)
            cursor.execute(sub_upsert_stmt)

        logging.info("Subscriptions successfully created.")
        logging.info("Ok.")
