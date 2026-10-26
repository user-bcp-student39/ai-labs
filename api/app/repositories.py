import sqlite3


def list_task_records(connection: sqlite3.Connection, owner: str) -> list[sqlite3.Row]:
    return connection.execute(
        "SELECT id,title,description,status,owner,priority,created_at "
        "FROM tasks WHERE owner = ? ORDER BY id",
        (owner,),
    ).fetchall()


def create_task_record(
    connection: sqlite3.Connection,
    title: str,
    description: str,
    status: str,
    owner: str,
    priority: str,
) -> sqlite3.Row:
    cursor = connection.execute(
        "INSERT INTO tasks(title,description,status,owner,priority,created_at) "
        "VALUES (?,?,?,?,?,datetime('now'))",
        (title, description, status, owner, priority),
    )
    connection.commit()
    row = connection.execute(
        "SELECT id,title,description,status,owner,priority,created_at FROM tasks WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    if row is None:
        raise RuntimeError("Created task could not be retrieved")
    return row


def list_summary_records(connection: sqlite3.Connection, owner: str) -> list[sqlite3.Row]:
    return connection.execute(
        "SELECT status,priority FROM tasks WHERE owner = ?",
        (owner,),
    ).fetchall()
