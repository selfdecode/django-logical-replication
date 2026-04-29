# Django Logical Replication

A Django package to sync tables across environments using PostgreSQL logical replication.

## Overview

This package enables PostgreSQL logical replication to sync specific tables across environments while supporting:
- Relationships between synced and non-synced tables
- Denormalization of non-synced tables triggered by synced tables
- Deletion propagation across environments
- Non-destructive migration of existing environments

<!-- omit in toc -->
## Table of Contents

- [Overview](#overview)
- [Key Concepts](#key-concepts)
- [Setup](#setup)
  - [One - Install Package + Add to `requirements.txt`](#one---install-package--add-to-requirementstxt)
  - [Two - Add IS\_MASTER\_ENV to settings.py](#two---add-is_master_env-to-settingspy)
  - [Three - Register Models](#three---register-models)
  - [Four - Add Database Router](#four---add-database-router)
  - [Five - Add Cron Classes (Optional)](#five---add-cron-classes-optional)
  - [Six - Setup Publications + Subscriptions](#six---setup-publications--subscriptions)
    - [New Env](#new-env)
    - [Existing Env](#existing-env)
    - [Creating Subscription](#creating-subscription)
- [Continuous Deployment](#continuous-deployment)
- [Delete Models](#delete-models)
  - [How it Works](#how-it-works)
- [Denormalize Models](#denormalize-models)
  - [How it Works](#how-it-works-1)
- [Advanced Publication Options](#advanced-publication-options)
  - [Row and Column Filtering](#row-and-column-filtering)
- [Caveats](#caveats)
  - [1. Avoid Inserting Into System Tables on Slave Environment](#1-avoid-inserting-into-system-tables-on-slave-environment)
  - [2. Required Django Contrib Models](#2-required-django-contrib-models)
- [Tests](#tests)
  - [Disabling Replication Signals](#disabling-replication-signals)
- [Non-Destructive Manual Resync](#non-destructive-manual-resync)
  - [Option 1: Using System Table Dump](#option-1-using-system-table-dump)
  - [Option 2: Using Subscription Reset](#option-2-using-subscription-reset)
- [Common Issues \& Solutions](#common-issues--solutions)
  - [Primary Key Conflicts](#primary-key-conflicts)
  - [Missing Foreign Keys](#missing-foreign-keys)
  - [Django Content Types break sync](#django-content-types-break-sync)


## Key Concepts

| Term | Description |
|------|-------------|
| Master Environment | Source of truth (`IS_MASTER_ENV = True`) |
| Slave Environment | Receives synced data (`IS_MASTER_ENV = False`) |
| User Model | Non-synced model (default) |
| System Model | Model synced across environments via `@system_model` |
| Delete Model | System model with managed deletions via `@delete_model` |
| Denormalize Model | Delete model with denormalization via `@denormalize_model` |


## Setup

### One - Install Package + Add to `requirements.txt`

```python
# requirements.txt
pip install git+https://github.com/selfdecode/django-logical-replication.git@v2.0.2
```

Add to installed apps:

```python
# settings.py
INSTALLED_APPS = [
    "...",
    "logical_replication",
]
```


### Two - Add IS_MASTER_ENV to settings.py

```python
# settings.py
IS_MASTER_ENV = os.environ["IS_MASTER_ENV"] == "true"
```


### Three - Register Models

Either use a decorator:

```python
# models.py
@system_model
class Unit(models.Model):
    pass
```

Or register in settings:

```python
# settings.py
ADDITIONAL_SYSTEM_MODELS = ["dummy_app.Unit"]
ADDITIONAL_DELETE_MODELS = ["dummy_app.Marker"]
ADDITIONAL_DENORMALIZE_MODELS = ["dummy_app.Outcome_sub_outcomes"]  # many2many
```

**Hint:** You can call `update_publication --dry-run` to get a list of all user models. Make sure nothing you want to sync is included in here.


### Four - Add Database Router

This router controls migration on slave envs for synced django contrib models. It should be placed **first**.

```python
# settings.py
DATABASE_ROUTERS = ["logical_replication.router.LogicalReplicationRouter"]
```


### Five - Add Cron Classes (Optional)

These cron classes are required only if you're using delete models or denormalize models. They handle:
- Delete propagation across environments (for delete models)
- Denormalization updates (for denormalize models)

```python
# settings.py
CRON_CLASSES = [
    # ...
    "logical_replication.cron.ProcessDeleteQueue",     # Required for delete models
    "logical_replication.cron.ProcessDenormalizeQueue", # Required for denormalize models
]
```

**Skip this step** if you are only using system models without delete/denormalize functionality.

**Dependencies:**
This feature requires the [django-cron package](https://django-cron.readthedocs.io/en/latest/installation.html). If you're using these cron classes, you'll need to:
1. Add django-cron to `INSTALLED_APPS`
2. Periodly run `python manage.py runcrons`
(see django-cron docs for more details)

### Six - Setup Publications + Subscriptions

#### New Env

**Steps:**
1. Setup tables on new slave env:
   ```bash
   manage.py create_django_contrib_tables  # must run BEFORE migrate
   manage.py migrate
   ```

2. Create empty publication on master:
   ```bash
   manage.py create_publication  # if doesn't exist
   ```

3. Create subscription on slave ([details](#creating-subscription)):
   ```bash
   manage.py create_subscription
   ```

4. Update publication on master with tables to sync:
   ```bash
   manage.py update_publication
   ```

5. Update subscription on slave:
   ```bash
   manage.py update_subscription  # This will trigger initial copy of tables!
   ```

See the `dummy_app.tests.py` for an example (steps 2-3 are already done in docker-compose).

#### Existing Env

The initial sync uses a simple `COPY FROM` so will fail if constraints are violated (e.g., primary key or unique).

**Caveats:**
- The database will be no-operation for a while
- Although user data will not be lost, newly missing FKs will be handled as though `on_delete` was called

**Steps:**

1. Create empty publication on master:
   ```bash
   manage.py create_publication  # if doesn't exist
   ```

2. Create subscription on slave ([details](#creating-subscription)):
   ```bash
   manage.py create_subscription
   ```

3. Build delete sql:
   ```bash
   print_delete_sql > delete.sql
   ```

4. Run `delete.sql` on **slave** env:
   - This will delete all data in system tables on slave
   - **Warning:** Does NOT handle row filters

5. Update publication on master with tables to sync:
   ```bash
   manage.py update_publication
   ```

6. Update subscription on slave:
   ```bash
   manage.py update_subscription  # This will trigger initial copy of tables!
   ```

7. Resync missing FKs on slave:
   ```bash
   manage.py resync_user_table_fks  # Note: may DELETE user data for hanging rows
   ```

#### Creating Subscription

To create a subscription, a connection string must be provided to allow the slave db to connect to master. For example:
```
'dbname=reports host=master user=user password=password'
```

**Important:** Subscriptions can only be managed by superuser. Your django app must have superuser access to use the `create_subscription` command.


**Custom Connection String:**
```bash
manage.py create_subscription -c 'dbname=reports host=master user=user password=password'
```

If no string is provided, credentials will be fetched from AWS Secrets Manager using:
- `REPLICATION_CONNECTION_SECRET`
- `REPLICATION_CONNECTION_SECRET_REGION` (defaults to "us-east-1")

The secret should contain all the keys above (dbname will default to `PROJECT_SLUG`).

**Note:** boto3 must be installed to use this feature.


## Continuous Deployment

The following order is recommended:

1. deploy code changes + migrate db on master
2. `manage update_publication` on master
3. `manage populate_content_types` on master (see [here](#django-content-types-break-sync))
4. deploy code changes + migrate db on slave
5. `manage update_subscription` on slave

On error, there will be automatic retries so a slight delay in deployment finish across master + slave should resolve itsef.

`update_subscription` must be called after `update_publication` for any new tables to be synced.


## Delete Models

Only insert + update operations of delete models are synced automatically to slave environments. Delete operations are instead logged to the synced `DeleteQueue` table.

### How it Works

1. When a delete model is deleted on the master environment, the operation is logged to the `DeleteQueue` table
2. A cron job that runs only on slave environments processes the delete queue
3. Each object is manually deleted through the `.delete()` method
4. Any dependent models are handled according to Django's `on_delete` configuration


**Important:** Any system model upon which user models depend (via a FK or OneToOneField) must be marked as a delete model. This package will throw an error if it detects this situation.

**Note:** Although the delete queue on slave environments will be deleted after processing, by default the master queue is kept indefinitely. To expire master queue rows, add the following to `settings.py`:
```python
EXPIRE_DELETE_QUEUE_AFTER = 30  # days
```


## Denormalize Models

Denormalize models are designed to accommodate denormalization in user models based on data stored in system models. When a system model used for denormalization is changed, the user models must be updated (or marked as stale to be updated later).

### How it Works

1. When a denormalize model is updated or inserted, the operation is logged to the synced `DenormalizeQueue` table
2. A cron job that runs only on slave environments processes the denormalize queue
3. The cron job will call `.save()`, thereby triggering the denormalize post-save signal on the slave environments

Denormalize models are also delete models, so denormalization due to `post_delete` will also be handled.

**Note:** Although the denormalize queue on slave environments will be deleted after processing, by default the master queue is kept indefinitely. To expire master queue rows, add the following to `settings.py`:
```python
EXPIRE_DENORMALIZE_QUEUE_AFTER = 30  # days
```


## Advanced Publication Options

PostgreSQL supports syncing only a subset of columns or a subset of rows. See details in the [PostgreSQL documentation](https://www.postgresql.org/docs/current/sql-createpublication.html).

### Row and Column Filtering

You can specify filters via the `ADDITIONAL_PUBLICATION_SETTINGS` constant in `settings.py`. The format is `{model_str: sql}`. The SQL should be correctly encoded using `sql` from `psycopg2` package.

Example:
```python
from psycopg2 import sql

ADDITIONAL_PUBLICATION_SETTINGS = {
    "dummy_app.Outcome": sql.SQL("WHERE ({col_name} != 'test')").format(
        col_name=sql.Identifier("name")
    )
}
```

**Important Notes:**
- You may need to run `ALTER TABLE table_name REPLICA IDENTITY FULL;` when using a row filter
- To skip validation that blocks system models from having FKs to user models:
  ```python
  SKIP_VALIDATION_MODELS = ["dummy_app.Outcome"]
  ```


## Caveats

### 1. Avoid Inserting Into System Tables on Slave Environment

Duplicate primary keys or violated unique constraints will throw an exception and block all subsequent syncing.

**Solutions:**
- If you must insert data, use UUIDs instead of auto-incrementing primary keys
- The package provides admin utilities to prevent inserting/editing on slave environments:
  ```python
  @admin_register
  class MyModelAdmin(admin.ModelAdmin):
      # This decorator automatically blocks model changes on slave environments
      pass
  ```

### 2. Required Django Contrib Models

Certain Django contrib models must be synced:
- `django_content_types`
- All tables in the auth app

These are synced by default as there is no reliable way to avoid this without risking Django content types becoming out of sync.


## Tests

### Disabling Replication Signals

You can disable logical replication signals during testing by adding the following to `settings.py`:
```python
DISABLE_LOGICAL_REPLICATION_SIGNALS = True
```

**Important:** Delete and denormalize models require signals to be enabled for proper synchronization.


## Non-Destructive Manual Resync

### Option 1: Using System Table Dump

1. Generate the `pg_dump` command:
   ```bash
   manage.py print_dump_system_tables
   ```

2. Drop existing system tables:
   ```bash
   manage.py print_delete_sql | psql your_database
   ```

3. Apply the dump to target environment

4. Resync foreign keys:
   ```bash
   manage.py resync_user_table_fks
   ```

### Option 2: Using Subscription Reset

1. Drop the subscriptions
2. Drop the system tables
3. Re-create the subscriptions (this triggers initial data copy)
4. Resync foreign keys:
   ```bash
   manage.py resync_user_table_fks
   ```


## Common Issues & Solutions

### Primary Key Conflicts

**Problem:** Auto-incrementing IDs can cause sync conflicts in slave environments.

**Solution:** Use UUIDs instead of auto-incrementing IDs when inserting data in slave environments.

### Missing Foreign Keys

**Problem:** Foreign key relationships may break during synchronization.

**Solutions:**
1. Run the resync command:
   ```bash
   manage.py resync_user_table_fks
   ```

2. Verify system model configuration:
   - Check that all required system models are properly marked
   - Review foreign key relationships between system and user models

### Django Content Types break sync

**Problem:** Django content types are lazily created, meaning they're only created when first accessed. If a slave environment tries to access a content type before the master environment, it will create its own content type record. This leads to unique constraint violations when the master's content type record is synced.

**Solution:**
Force content type creation on the master environment by running:
```bash
python manage.py populate_content_types
```

**When to run:** Execute this command on the master environment after:
1. Running migrations
2. Updating the publication
3. Before any slave environments access the system

This ensures content types are created on the master first and properly synced to slave environments.
