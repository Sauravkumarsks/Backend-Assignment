import sqlite3
from typing import Tuple, Dict, Any, List, Optional

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    from_msisdn TEXT NOT NULL,
    to_msisdn   TEXT NOT NULL,
    ts          TEXT NOT NULL,   -- ISO-8601 UTC string
    text        TEXT,
    created_at  TEXT NOT NULL     -- server time ISO-8601
);
"""

def get_conn(database_url: str) -> sqlite3.Connection:
    # Expecting sqlite:////data/app.db
    if not database_url.startswith("sqlite:////"):
        raise ValueError("DATABASE_URL must be like sqlite:////path/to.db")
    path = database_url.replace("sqlite:////", "/")
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    with conn:
        conn.executescript(SCHEMA_SQL)


def ready(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1")
        return True
    except Exception:
        return False


def insert_message(conn: sqlite3.Connection, payload: Dict[str, Any]) -> Tuple[bool, bool, Optional[str]]:
    """
    Returns: (created, duplicate, err)
    - created=True if inserted
    - duplicate=True if message_id already exists
    - err=error string if unexpected DB error
    """
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO messages (message_id, from_msisdn, to_msisdn, ts, text, created_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    payload["message_id"],
                    payload["from"],
                    payload["to"],
                    payload["ts"],
                    payload.get("text"),
                ),
            )
        return True, False, None
    except sqlite3.IntegrityError as e:
        # Duplicate primary key
        return False, True, None
    except Exception as e:
        return False, False, str(e)


def list_messages(
    conn: sqlite3.Connection,
    limit: int,
    offset: int,
    from_filter: Optional[str],
    since: Optional[str],
    q: Optional[str],
) -> Tuple[List[Dict[str, Any]], int]:
    where = []
    params: List[Any] = []

    if from_filter:
        where.append("from_msisdn = ?")
        params.append(from_filter)
    if since:
        where.append("ts >= ?")
        params.append(since)
    if q:
        where.append("LOWER(text) LIKE ?")
        params.append(f"%{q.lower()}%")

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    total = conn.execute(
        f"SELECT COUNT(*) AS c FROM messages {where_sql}",
        params,
    ).fetchone()["c"]

    rows = conn.execute(
        f"""
        SELECT message_id, from_msisdn, to_msisdn, ts, text
        FROM messages
        {where_sql}
        ORDER BY ts ASC, message_id ASC
        LIMIT ? OFFSET ?
        """,
        params + [limit, offset],
    ).fetchall()

    data = []
    for r in rows:
        data.append({
            "message_id": r["message_id"],
            "from": r["from_msisdn"],
            "to": r["to_msisdn"],
            "ts": r["ts"],
            "text": r["text"],
        })
    return data, total


def stats(conn: sqlite3.Connection) -> Dict[str, Any]:
    total = conn.execute("SELECT COUNT(*) AS c FROM messages").fetchone()["c"]

    senders = conn.execute(
        """
        SELECT from_msisdn AS from, COUNT(*) AS count
        FROM messages
        GROUP BY from_msisdn
        ORDER BY count DESC
        LIMIT 10
        """
    ).fetchall()
    messages_per_sender = [{"from": r["from"], "count": r["count"]} for r in senders]

    first_row = conn.execute(
        "SELECT ts FROM messages ORDER BY ts ASC, message_id ASC LIMIT 1"
    ).fetchone()
    last_row = conn.execute(
        "SELECT ts FROM messages ORDER BY ts DESC, message_id DESC LIMIT 1"
    ).fetchone()

    return {
        "total_messages": total,
        "senders_count": len(messages_per_sender),
        "messages_per_sender": messages_per_sender,
        "first_message_ts": first_row["ts"] if first_row else None,
        "last_message_ts": last_row["ts"] if last_row else None,
    }
