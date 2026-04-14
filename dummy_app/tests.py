# pylint: disable=attribute-defined-outside-init,too-many-instance-attributes
from time import sleep, time

import pytest
from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core import management
from django.db import connections

from dummy_app.models import Category, Marker, Outcome, Result, Unit
from logical_replication.models import DeleteQueue, DenormalizeQueue
from logical_replication.utils import (
    does_user_table_depend_on,
    is_delete_model,
    is_denormalize_model,
    is_system_model,
    is_user_model,
    validate_no_system_to_user_dep,
)


class TestModelClassification:
    """Unit tests for model classification utilities - no DB setup needed."""

    def test_does_user_table_depend_on(self):
        assert not does_user_table_depend_on(Unit)
        assert does_user_table_depend_on(Outcome)
        assert does_user_table_depend_on(Marker)

    def test_validate_no_system_to_user_dep(self):
        assert validate_no_system_to_user_dep(Marker)
        Unit._meta.system_model = False
        try:
            with pytest.raises(ValueError):
                validate_no_system_to_user_dep(Marker)
        finally:
            Unit._meta.system_model = True

    def test_synced_contrib_models(self):
        Log = apps.get_model("admin", "LogEntry")
        assert is_user_model(Log)

        assert is_system_model(ContentType)
        assert is_delete_model(ContentType)
        assert not is_denormalize_model(ContentType)

        Group = apps.get_model("auth", "Group")
        assert is_system_model(Group)
        assert not is_delete_model(Group)

    def test_queue_models(self):
        for model_class in (DeleteQueue, DenormalizeQueue):
            assert is_system_model(model_class)
            assert is_delete_model(model_class)
            assert not is_denormalize_model(model_class)


@pytest.mark.django_db(transaction=True, databases="__all__")
class TestLogicalReplication:
    """Integration tests for logical replication - uses real databases."""

    def wait_for_sync(self, timeout=30, check_interval=0.1):
        """Wait for logical replication to catch up by polling subscription status."""
        start_time = time()
        while time() - start_time < timeout:
            with connections["slave"].cursor() as cursor:
                cursor.execute(
                    """
                    SELECT subname,
                        received_lsn = latest_end_lsn AS is_caught_up,
                        received_lsn IS NOT NULL AS is_receiving
                    FROM pg_catalog.pg_stat_subscription
                    WHERE subname IN (
                        'django_logical_replication_sub',
                        'django_logical_replication_upsert_sub'
                    );
                """
                )
                rows = cursor.fetchall()

                # Check all up to date
                all_caught_up = all(
                    is_caught_up and is_receiving
                    for _, is_caught_up, is_receiving in rows
                )

                if all_caught_up:
                    return

            sleep(check_interval)

    def setup_tables(self):
        self.wait_for_sync()  # let any old operations finish

        # Drop subscriptions first (on slave), then publications (on master)
        # These are database-level objects, not dropped with schema
        with connections["slave"].cursor() as cursor:
            cursor.execute(
                "SELECT subname FROM pg_subscription WHERE subname LIKE 'django_logical_replication%'"
            )
            for (subname,) in cursor.fetchall():
                cursor.execute(f'DROP SUBSCRIPTION IF EXISTS "{subname}"')

        with connections["default"].cursor() as cursor:
            cursor.execute(
                "SELECT pubname FROM pg_publication WHERE pubname LIKE 'django_logical_replication%'"
            )
            for (pubname,) in cursor.fetchall():
                cursor.execute(f'DROP PUBLICATION IF EXISTS "{pubname}"')

        # drop tables
        for db_ in ("slave", "default"):
            with connections[db_].cursor() as cursor:
                cursor.execute("DROP SCHEMA public CASCADE;")
                cursor.execute("CREATE SCHEMA public")

        # rebuild
        # set up master
        management.call_command("migrate")
        with connections["default"].cursor() as cursor:
            cursor.execute("ALTER TABLE dummy_app_outcome REPLICA IDENTITY FULL;")

        # set up slave
        management.call_command(
            "create_django_contrib_tables", override_env=True, db="slave"
        )
        management.call_command("migrate", database="slave")

    def setup_logical_replication(self, setup_tables=True, dont_copy=False):
        if setup_tables:
            self.setup_tables()

        # Create publications/subscriptions
        management.call_command("create_publication", override_env=True)
        management.call_command(
            "create_subscription",
            override_env=True,
            db="slave",
            connection_string="dbname=django_logical_replication host=master user=django_logical_replication password=password",
        )

        management.call_command("update_publication")
        management.call_command(
            "update_subscription",
            override_env=True,
            db="slave",
            dont_copy_data=dont_copy,
        )

    def populate_db(self):
        self.unit1 = Unit.objects.create(symbol="g")
        self.unit2 = Unit.objects.create(symbol="kg")

        self.category1 = Category.objects.create(name="brain")
        self.category2 = Category.objects.create(name="blood")

        self.marker1 = Marker.objects.create(name="Weight", unit=self.unit1)
        self.marker2 = Marker.objects.create(name="Weight (kg)", unit=self.unit2)

        self.outcome1 = Outcome.objects.create(name="bad")
        self.outcome2 = Outcome.objects.create(name="good")
        self.outcome2.categories.add(self.category1, self.category2)

        self.master_result1 = Result.objects.create(
            marker=self.marker1, outcome=self.outcome1, outcome_name=self.outcome1.name
        )
        self.master_result1.sub_outcomes.add(self.outcome2)

        self.master_result2 = Result.objects.create(
            marker=self.marker2, outcome=self.outcome2, outcome_name=self.outcome2.name
        )

    def test_initial_sync_copy(self):
        self.setup_tables()

        # data on master
        self.populate_db()

        # different data on slave
        # duplicate ids will cause error !!
        unit1 = Unit.objects.using("slave").create(id=100, symbol="g (slave)")
        marker1 = Marker.objects.using("slave").create(
            id=100, name="Weight(slave)", unit=unit1
        )
        outcome1 = Outcome.objects.using("slave").create(id=100, name="ok")
        outcome2 = Outcome.objects.using("slave").create(id=101, name="hello")
        slave_result = Result.objects.using("slave").create(
            marker=marker1, outcome=outcome1, outcome_name=outcome1.name
        )
        Result.sub_outcomes.through.objects.using("slave").create(
            result=slave_result, outcome=outcome2
        )

        self.setup_logical_replication(setup_tables=False)
        self.wait_for_sync()

        # rows of master copied over (no deletes )
        assert Unit.objects.using("slave").all().count() == 2 + 1

        # system many2many tables copied
        assert self.outcome2.categories.using("slave").all().count() == 2

        # user tables unaffected
        results = Result.objects.using("slave").all()
        assert len(results) == 1
        assert results[0].pk == slave_result.pk
        assert Result.sub_outcomes.through.objects.using("slave").all().count() == 1

    def test_initial_sync_with_update(self):
        self.setup_tables()

        # data on master
        self.populate_db()

        unit1 = Unit.objects.using("slave").create(symbol="g (slave)")
        marker1 = Marker.objects.using("slave").create(name="Weight(slave)", unit=unit1)
        marker2 = Marker.objects.using("slave").create(
            name="Weight(slave)2", unit=unit1
        )
        marker3 = Marker.objects.using("slave").create(
            id=100, name="Will be deleted", unit=unit1
        )
        outcome1 = Outcome.objects.using("slave").create(name="ok")
        outcome2 = Outcome.objects.using("slave").create(id=100, name="will be deleted")
        slave_result = Result.objects.using("slave").create(
            marker=marker1, outcome=outcome1, outcome_name=outcome1.name
        )
        slave_result2 = Result.objects.using("slave").create(
            marker=marker3, outcome=outcome1, outcome_name=outcome1.name
        )
        slave_result3 = Result.objects.using("slave").create(
            marker=marker2, outcome=outcome2, outcome_name=outcome2.name
        )
        Result.sub_outcomes.through.objects.using("slave").create(
            result=slave_result, outcome=outcome2
        )

        # steps
        # 1. disable triggers for all user tables on slave
        # 2. delete all system tables on slave
        # 3. sync
        # 4. reenable triggers
        # 5. run resync Fks cmd
        with connections["slave"].cursor() as cursor:
            cursor.execute("SET session_replication_role = 'replica';")
            # avoid django on_delete
            cursor.execute("DELETE FROM dummy_app_marker;")
            cursor.execute("DELETE FROM dummy_app_outcome;")
            cursor.execute("DELETE FROM dummy_app_unit;")

        # results not deleted
        assert Result.objects.using("slave").count() == 3

        self.setup_logical_replication(setup_tables=False)
        self.wait_for_sync()

        assert Unit.objects.using("slave").count() == 2
        assert Marker.objects.using("slave").count() == 2
        assert Outcome.objects.using("slave").count() == 2
        assert Result.objects.using("slave").count() == 3
        assert Result.sub_outcomes.through.objects.using("slave").count() == 1

        with connections["slave"].cursor() as cursor:
            cursor.execute("SET session_replication_role = 'origin';")

        management.call_command("resync_user_table_fks", override_env=True, db="slave")

        slave_result.refresh_from_db()
        assert slave_result.marker_id == marker1.pk
        assert slave_result.outcome_id == outcome1.pk
        assert slave_result.outcome_name == outcome1.name

        slave_result3.refresh_from_db()
        assert slave_result3.marker_id == marker2.pk
        assert slave_result3.outcome_id is None  # SET_NULl
        assert slave_result3.outcome_name == outcome2.name  # Not denomralized!

        assert not Result.objects.using("slave").filter(pk=slave_result2.pk).exists()
        assert not Result.sub_outcomes.through.objects.using("slave").all().exists()

    def test_basic_replication(self):
        self.setup_logical_replication()
        self.populate_db()

        # on master
        assert Unit.objects.count() == 2
        assert Marker.objects.count() == 2
        assert Outcome.objects.count() == 2
        assert Outcome.categories.through.objects.count() == 2
        assert Result.objects.count() == 2

        self.wait_for_sync()

        # on slave
        assert Unit.objects.using("slave").count() == 2
        assert Marker.objects.using("slave").count() == 2
        assert Outcome.objects.using("slave").count() == 2
        assert Outcome.categories.through.objects.using("slave").count() == 2
        assert Result.objects.using("slave").count() == 0  # not synced

        # row filter correctly applied
        # see ADDITIONAL_PUBLICATION_SETTINGS (name != 'test')
        Outcome.objects.create(name="something")
        self.wait_for_sync()
        assert Outcome.objects.using("slave").filter(name="something").exists()

        Outcome.objects.create(name="test")
        self.wait_for_sync()
        assert not Outcome.objects.using("slave").filter(name="test").exists()

    def test_delete_set_null(self, settings):  # pylint: disable=redefined-outer-name
        self.setup_logical_replication()
        self.populate_db()
        self.wait_for_sync()

        slave_result = Result.objects.using("slave").create(
            marker=self.marker1, outcome=self.outcome1, outcome_name=self.outcome1.name
        )

        self.outcome1.delete()  # on master
        self.master_result1.refresh_from_db()
        assert self.master_result1.outcome_id is None
        assert self.master_result1.outcome_name == ""

        self.wait_for_sync()
        # outcome is not deleted on slave yet
        slave_outcome = Outcome.objects.using("slave").get(name=self.outcome1.name)
        # instead added to delete queue
        delete_queue = DeleteQueue.objects.using("slave").first()
        assert delete_queue.object_pk == str(slave_outcome.pk)
        assert delete_queue.content_type.model_class() == Outcome

        # process delete queue
        settings.IS_MASTER_ENV = False
        delete_queue.process_object()  # on slave

        # Outcome deleted + linked result denormalized
        assert not Outcome.objects.filter(name=slave_outcome.name).exists()
        slave_result.refresh_from_db(using="slave")
        assert slave_result.outcome_id is None
        assert slave_result.outcome_name == ""
        settings.IS_MASTER_ENV = True

    def test_delete_cascade(self, settings):  # pylint: disable=redefined-outer-name
        self.setup_logical_replication()
        self.populate_db()
        self.wait_for_sync()

        slave_result = Result.objects.using("slave").create(
            marker=self.marker1, outcome=self.outcome1, outcome_name=self.outcome1.name
        )

        self.unit1.delete()  # on master
        assert not Marker.objects.filter(pk=self.marker1.pk).exists()
        assert not Result.objects.filter(pk=self.master_result1.pk).exists()

        self.wait_for_sync()
        # unit is deleted
        # marker is not yet
        assert not Unit.objects.using("slave").filter(pk=self.marker1.unit_id).exists()
        assert Marker.objects.using("slave").filter(pk=self.marker1.pk).exists()
        assert Result.objects.using("slave").filter(pk=slave_result.pk).exists()

        # instead added to delete queue
        delete_queue = DeleteQueue.objects.using("slave").first()
        assert delete_queue.object_pk == str(self.marker1.pk)
        assert delete_queue.content_type.model_class() == Marker

        # process delete queue
        settings.IS_MASTER_ENV = False
        delete_queue.process_object()
        assert not Marker.objects.using("slave").filter(pk=self.marker1.pk).exists()
        assert not Result.objects.using("slave").filter(pk=slave_result.pk).exists()

        settings.IS_MASTER_ENV = True

    def test_denormalize(self):
        self.setup_logical_replication()
        self.populate_db()
        self.wait_for_sync()

        slave_result = Result.objects.using("slave").create(
            marker=self.marker1, outcome=self.outcome1, outcome_name=self.outcome1.name
        )

        new_name = "new_name"
        self.outcome1.name = new_name  # on master
        self.outcome1.save()
        self.master_result1.refresh_from_db()
        assert self.master_result1.outcome_name == new_name

        self.wait_for_sync()
        # outcome changed synced immediately
        slave_outcome = Outcome.objects.using("slave").get(pk=self.outcome1.pk)
        assert slave_outcome.name == new_name
        # entry added to denormalize queue
        denormalize_queue = DenormalizeQueue.objects.using("slave").first()
        assert denormalize_queue.object_pk == str(slave_outcome.pk)
        assert denormalize_queue.content_type.model_class() == Outcome

        # process delete queue
        settings.IS_MASTER_ENV = False
        denormalize_queue.process_object()  # on slave

        # slave result denormalized
        slave_result.refresh_from_db(using="slave")
        assert slave_result.outcome_name == new_name
        settings.IS_MASTER_ENV = True

    def test_dont_copy_flag(self):
        self.setup_tables()

        # data on master
        self.populate_db()
        slave_unit1 = Unit.objects.using("slave").create(symbol="g")

        # Create publications/subscriptions first
        management.call_command("create_publication", override_env=True)
        management.call_command(
            "create_subscription",
            override_env=True,
            db="slave",
            connection_string="dbname=django_logical_replication host=master user=django_logical_replication password=password",
        )

        # sync django content types first (otherwise errors)
        with connections["default"].cursor() as cursor:
            cursor.execute(
                """
                ALTER PUBLICATION "django_logical_replication_upsert_pub"
                SET TABLE "auth_permission", "auth_group_permissions", "auth_group",
                "auth_user_groups", "auth_user_user_permissions", "auth_user",
                "django_content_type";
                """
            )
        management.call_command("update_subscription", override_env=True, db="slave")
        self.wait_for_sync()

        assert ContentType.objects.using("slave").exists()

        # now update publications with all tables, using dont_copy flag
        management.call_command("update_publication")
        management.call_command(
            "update_subscription",
            override_env=True,
            db="slave",
            dont_copy_data=True,
        )
        self.wait_for_sync()

        # nothing copied
        assert Unit.objects.using("slave").all().count() == 1
        assert Marker.objects.using("slave").all().count() == 0

        unit3 = Unit.objects.create(symbol="new unit")  # new are copied
        # updates fail if no matching row found in slave
        self.unit1.symbol = "updated g"
        self.unit1.save()
        self.unit2.symbol = "updated kg"
        self.unit2.save()

        self.wait_for_sync()

        assert Unit.objects.using("slave").count() == 2
        assert Unit.objects.using("slave").filter(pk=unit3.pk).exists()
        assert not Unit.objects.using("slave").filter(pk=self.unit2.pk).exists()

        slave_unit1.refresh_from_db()
        assert slave_unit1.symbol == self.unit1.symbol
