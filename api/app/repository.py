import sqlite3

SELECT_TASKS_SQL = "SELECT id,title,description,status,owner,priority,created_at FROM tasks"
INSERT_TASK_SQL = "INSERT INTO tasks(title,description,status,owner,priority,created_at) VALUES (?,?,?,?,?,datetime('now'))"


def find_tasks_by_owner(connection: sqlite3.Connection, owner: str) -> list[sqlite3.Row]:
    return connection.execute(SELECT_TASKS_SQL + " WHERE owner = ? ORDER BY id", (owner,)).fetchall()


def find_status_and_priority_by_owner(connection: sqlite3.Connection, owner: str) -> list[sqlite3.Row]:
    return connection.execute("SELECT status,priority FROM tasks WHERE owner = ?", (owner,)).fetchall()


def insert_task(
    connection: sqlite3.Connection,
    title: str,
    description: str,
    status: str,
    owner: str,
    priority: str,
) -> int:
    cursor = connection.execute(INSERT_TASK_SQL, (title, description, status, owner, priority))
    connection.commit()
    return int(cursor.lastrowid)


def find_task_by_id(connection: sqlite3.Connection, task_id: int) -> sqlite3.Row:
    return connection.execute(SELECT_TASKS_SQL + " WHERE id = ?", (task_id,)).fetchone()
