"""Check whether the human-managed services and keys are ready.

Run:
    python setup_check.py

This script does not fix anything automatically. It tells you what still needs
human setup: PostgreSQL, Redis, and free provider API keys.
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv()


def check_env(name: str) -> bool:
    value = os.getenv(name, "").strip()
    ok = bool(value) and "Your Name" not in value
    print(f"{'OK' if ok else 'MISSING'} {name}", flush=True)
    return ok


def check_redis() -> bool:
    try:
        from storage.redis_client import get_redis_client

        get_redis_client().ping()
        print("OK Redis connection", flush=True)
        return True
    except Exception as exc:
        print(f"MISSING Redis connection: {exc}", flush=True)
        return False


def check_postgres() -> bool:
    try:
        from storage.postgres import init_db

        init_db()
        print("OK PostgreSQL connection and summaries table", flush=True)
        return True
    except Exception as exc:
        print(f"MISSING PostgreSQL/pgvector setup: {exc}", flush=True)
        return False


def main() -> int:
    checks = [
        check_env("DATABASE_URL"),
        check_env("REDIS_URL"),
        check_env("GROQ_API_KEY"),
        check_env("NVIDIA_API_KEY"),
        check_env("GEMINI_API_KEY"),
        check_env("SEC_EDGAR_USER_AGENT"),
        check_redis(),
        check_postgres(),
    ]
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
