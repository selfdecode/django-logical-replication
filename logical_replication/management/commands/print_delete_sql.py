from django.core.management.base import BaseCommand

from logical_replication.utils.replication import get_system_models


class Command(BaseCommand):
    help = "Generates sql for deleting all system models"

    def handle(self, *_args, **_kwargs):
        sql_statements: list[str] = ["SET session_replication_role = 'replica';"]

        for system_model in get_system_models():
            sql_statements.append(
                f"DELETE FROM {system_model._meta.db_table};"  # nosec
            )

        sql_statements.append("SET session_replication_role = 'origin';")

        print("\n\n".join(sql_statements))  # noqa
