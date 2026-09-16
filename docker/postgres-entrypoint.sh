#!/usr/bin/env bash
# Wrapper for the official postgres entrypoint: loads the passwords decrypted
# by ARTV6_db_secrets (docker/pythonpath_dev/decrypt_db_secrets.py) before initdb runs.
set -e

SECRETS_DIR=/run/db-secrets

if [ -s "$SECRETS_DIR/postgres_password" ]; then
  POSTGRES_PASSWORD="$(cat "$SECRETS_DIR/postgres_password")"
  export POSTGRES_PASSWORD
  EXAMPLES_PASSWORD="$(cat "$SECRETS_DIR/examples_password" 2>/dev/null || true)"
  export EXAMPLES_PASSWORD
elif [ ! -s "${PGDATA:-/var/lib/postgresql/data}/PG_VERSION" ]; then
  # Password is only needed on first init; an existing cluster can start without it
  echo "ERROR: $SECRETS_DIR/postgres_password missing and database is uninitialized" >&2
  exit 1
fi

exec docker-entrypoint.sh "$@"
