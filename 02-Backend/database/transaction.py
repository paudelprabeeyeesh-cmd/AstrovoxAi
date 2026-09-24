import sqlite3
from contextlib import contextmanager
from typing import Generator, Optional


@contextmanager
def transaction(
    conn: Optional[sqlite3.Connection] = None,
) -> Generator[sqlite3.Connection, None, None]:
    managed = False
    if conn is None:
        from database.connection import get_connection
        conn = get_connection()
        managed = True
    try:
        conn.execute("BEGIN")
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        if managed:
            conn.close()
