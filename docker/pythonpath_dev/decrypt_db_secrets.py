"""Decrypt Jasypt-encrypted DB passwords (encrypted with DATABASE_KEY).

Used in two places, so Superset and Postgres always get the same password:
  - superset_config.py:  from decrypt_db_secrets import decrypt
  - ARTV6_db_secrets service:  python decrypt_db_secrets.py
    writes the plain passwords into an in-memory (tmpfs) volume at
    /run/db-secrets, read by ARTV6_db via docker/postgres-entrypoint.sh
    (Postgres has no Python, so it cannot decrypt on its own).
"""

import importlib.util
import os
import sys

OUT_DIR = "/run/db-secrets"
HELPER = "/app/superset/security/decrypt_jasypt.py"

# Load the helper by path so we don't import the whole superset package.
spec = importlib.util.spec_from_file_location("decrypt_jasypt", HELPER)
decrypt_jasypt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(decrypt_jasypt)


def decrypt(name):
    """Return env var `name` decrypted with DATABASE_KEY (raw value if not encrypted)."""
    raw = os.getenv(name, "")
    key = os.getenv("DATABASE_KEY", "")
    if not raw:
        return ""
    if not key:
        return raw
    try:
        value = decrypt_jasypt.jasypt_decrypt(key, raw)
        print(f"{name} decrypted successfully via Jasypt")
        return value
    except Exception as e:
        print(f"Jasypt decryption failed for {name}, using raw value: {e}")
        return raw


def write(filename, value):
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(value)
    os.chmod(path, 0o600)


if __name__ == "__main__":
    # POSTGRES_PASSWORD falls back to DATABASE_PASSWORD so both always match.
    postgres_password = decrypt("POSTGRES_PASSWORD") or decrypt("DATABASE_PASSWORD")
    if not postgres_password:
        sys.exit("ERROR: neither POSTGRES_PASSWORD nor DATABASE_PASSWORD is set")

    os.makedirs(OUT_DIR, exist_ok=True)
    write("postgres_password", postgres_password)
    write("examples_password", decrypt("EXAMPLES_PASSWORD"))
