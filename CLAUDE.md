# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Django package enabling PostgreSQL logical replication to sync specific tables across master/slave environments. Handles relationships between synced and non-synced tables, deletion propagation, and denormalization triggers.

## Development Commands

```bash
# Start databases (required for tests)
docker compose up -d master slave

# Run all tests
uv run pytest

# Run single test
uv run pytest dummy_app/tests.py::TestClassName::test_method -v

# Run tests with coverage
uv run pytest --cov=logical_replication

# Pre-commit checks (ruff, mypy, bandit)
uv run pre-commit run --all-files

# Install dependencies
uv sync
```

## Architecture

### Model Classification Hierarchy

```
@system_model     → Full sync (insert, update, delete via WAL)
    ↓ extends
@delete_model     → Insert+update synced; deletes logged to DeleteQueue
    ↓ extends
@denormalize_model → Also logs saves to DenormalizeQueue for post_save triggers
```

### Environment Model

- **Master** (`IS_MASTER_ENV=True`): Source of truth, direct deletes
- **Slave** (`IS_MASTER_ENV=False`): No direct deletes on system models; cron jobs process queues

### Two Publication Strategy

- `{project}_pub`: Full sync for pure system models
- `{project}_upsert_pub`: Insert+update only for delete/denormalize models

### Key Validation Rule

System models cannot have FKs to user models. User models can depend on system models (validated by `does_user_table_depend_on()`).

## Code Layout

```
logical_replication/
├── models.py          → ReplicatedQueue base, DeleteQueue, DenormalizeQueue
├── event_handlers.py  → Signal handlers for queue population
├── cron.py            → ProcessDeleteQueue, ProcessDenormalizeQueue
├── router.py          → LogicalReplicationRouter (blocks contrib migrations on slave)
├── admin.py           → SystemModelAdminMixin (blocks edits on slave)
├── utils/
│   ├── decorators.py  → @system_model, @delete_model, @denormalize_model
│   ├── replication.py → Model classification logic (is_system_model, get_*_models, etc.)
│   └── commands.py    → Publication/subscription SQL builders
└── management/commands/
    ├── create_publication.py
    ├── update_publication.py
    ├── create_subscription.py
    ├── update_subscription.py
    ├── resync_user_table_fks.py
    └── populate_content_types.py

dummy_app/  → Test models demonstrating all patterns
sample_project/  → Django project for tests
```

## Testing

- Uses real PostgreSQL (master on 5432, slave on 5433)
- Signal control: `DISABLE_LOGICAL_REPLICATION_SIGNALS = True` in settings
- Multi-DB tests require: `@pytest.mark.django_db(transaction=True, databases="__all__")`

## Code Style

- Ruff for linting and formatting (88 char lines)
- Migrations excluded from all linting
- Conventional commits via commitizen
