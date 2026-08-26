import os
import sys
import time

import psycopg

from .core.config import Settings


def main():
    settings = Settings()
    deadline = time.time() + int(os.getenv("DB_WAIT_TIMEOUT", "90"))
    last_error = None
    while time.time() < deadline:
        try:
            conn = psycopg.connect(settings.database_url.replace("postgresql+psycopg://", "postgresql://"), connect_timeout=5)
            conn.close()
            return 0
        except Exception as exc:
            last_error = exc
            time.sleep(2)
    print(f"Database not ready: {last_error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
