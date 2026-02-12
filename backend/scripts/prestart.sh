#! /usr/bin/env bash

set -e
set -x

# Let the DB start
uv run python app/backend_pre_start.py
echo "backend_pre_start.py completed"

# Run migrations
uv run alembic upgrade head
echo "alembic migration completed"

# Create initial data in DB
uv run python app/initial_data.py
echo "initial data added in db"
