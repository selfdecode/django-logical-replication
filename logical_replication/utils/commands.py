from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.management.base import CommandParser
from django.db.models import Model
from psycopg import sql

from logical_replication.utils.replication import (
    get_additional_publication_settings,
    get_delete_models,
    get_full_sync_models,
    get_system_models,
)


def db_safe_project_slug() -> str:
    return settings.PROJECT_SLUG.replace("-", "_")


def get_publication_name() -> str:
    return f"{db_safe_project_slug()}_pub"


def get_upsert_only_publication_name() -> str:
    return f"{db_safe_project_slug()}_upsert_pub"


def get_subscription_name() -> str:
    return f"{db_safe_project_slug()}_sub"


def get_upsert_only_subscription_name() -> str:
    return f"{db_safe_project_slug()}_upsert_sub"


def build_publication_object(model_class: type[Model]) -> sql.Identifier | sql.Composed:
    table = sql.Identifier(model_class._meta.db_table)
    if additional_settings := get_additional_publication_settings(model_class):
        return sql.SQL("{table} {additional_settings}").format(
            table=table, additional_settings=additional_settings
        )

    return table


def build_full_sync_tables_sql() -> sql.Composed:
    tables_to_sync = [
        build_publication_object(model) for model in get_full_sync_models()
    ]
    return sql.SQL(", ").join(tables_to_sync)


def build_upsert_sync_tables_sql() -> sql.Composed:
    delete_tables = [build_publication_object(model) for model in get_delete_models()]
    return sql.SQL(", ").join(delete_tables)


def log_and_execute(cursor: Any, statement: str | sql.Composed) -> None:
    readable = (
        statement
        if isinstance(statement, str)
        else statement.as_string(cursor.connection)
    )
    logging.info(f"Executing: {readable}")
    cursor.execute(statement)


def add_custom_db_args(parser: CommandParser) -> None:
    parser.add_argument("--db", dest="db", type=str)
    parser.add_argument("--override_env", dest="override_env", action="store_true")


def build_dump_command() -> str:
    db_tables = [model._meta.db_table for model in get_system_models()]
    return (
        f"pg_dump --column-inserts -a -d {db_safe_project_slug()} "
        f"-t {' -t '.join(db_tables)}> system_tables.sql"
    )
