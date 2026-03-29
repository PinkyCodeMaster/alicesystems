#!/bin/sh
set -eu

cd /srv/alice/apps/hub-api

mkdir -p ./data ./logs

python -m alembic upgrade head

if [ "${ALICE_PRACTICE_SEED_BOOTSTRAP:-true}" = "true" ]; then
  python -m app.scripts.seed_practice_bootstrap_records
fi

exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
