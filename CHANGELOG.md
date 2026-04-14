## v2.0.2 (2026-03-13)

### Fix

- resync_user_table_fks cmd 2nd attempt

## v2.0.1 (2026-03-13)

### Fix

- resync_user_table_fks cmd

## v2.0.0 (2026-02-05)

### BREAKING CHANGES

- Migrate to Django 5.2+ / 6.0 (drops Django 4.x support)
- Migrate to psycopg3 (drops psycopg2 support)
- Requires Python 3.12+

### Feat

- Switch to uv for dependency management (replaces poetry)
- Switch to ruff for linting/formatting (replaces black, isort, flake8)
- Modernize type hints for Python 3.12+

### Fix

- Fix resolve_object() to use correct database via `using` parameter
- Fix test deadlocks caused by synchronous_commit=remote_apply
- Explicitly drop publications/subscriptions in test setup
- Replace sleep() with wait_for_sync() for faster tests
- Update CI to use uv and run pre-commit on runner

### Refactor

- Split unit tests into separate TestModelClassification class
- Clean up deprecated typing imports (Type -> type, List -> list)

## v1.11.1 (2024-12-06)

## v1.11.0 (2024-12-05)

### Feat

- ping for finish

### Refactor

- simplify deps

## v1.10.3 (2024-09-17)

### Fix

- remove dummy init.sql code

## v1.10.2 (2024-08-29)

### Fix

- null fk handling

## v1.10.1 (2024-08-29)

### Fix

- resync hanging rows cmd

## v1.10.0 (2024-04-11)

### Feat

- populate content types
- add django 4.2 compatibility

### Fix

- remove backend utils dep
- exclude sample project

## v1.9.0 (2024-03-07)

### Feat

- upgrade django to 4.2

## v1.8.0 (2024-03-06)

### Feat

- support python 3.12

## v1.7.0 (2024-02-27)

### Feat

- switch to poetry for dependency management

## v1.6.0 (2023-12-21)

### Feat

- support on protect

### Fix

- init slave

## v1.5.0 (2023-12-19)

### Feat

- register replicated user admin
- add admin_register decorator

### Fix

- bump python version
- break on first fail
- add explicit links

## v1.4.0 (2023-12-11)

### Feat

- support manual resync

## v1.3.3 (2023-12-04)

### Fix

- add None default for queue expiry

## v1.3.2 (2023-11-23)

### Fix

- allow disable signals

## v1.3.1 (2023-11-23)

### Fix

- allow skipping validation

## v1.3.0 (2023-11-22)

### Feat

- support advanced publciation settings
- add isort precommit hook

## v1.2.1 (2023-08-21)

### Fix

- meta migration

## v1.2.0 (2023-08-21)

### Feat

- add print delete sql

### Fix

- use _meta not Meta

## v1.1.4 (2023-08-18)

### Fix

- increase wait for sync time
- correctly infer contrib types

## v1.1.3 (2023-08-15)

### Fix

- connection string arg
- typing error
- log user_table on bad setup

## v1.1.2 (2023-08-14)

### Fix

- include version in setup.py

## v1.1.1 (2023-08-14)

### Fix

- tag format

## 1.1.0 (2023-08-14)

### Fix

- pyproject toml

## 1.1.0 (2023-08-14)

### Fix

- pyproject toml

## v1.1.0 (2023-07-26)

### Feat

- add github workflow
- setup package
- add docker compose
- dummy app for tests
- logical replication package
- setup sample project app

### Fix

- ci
