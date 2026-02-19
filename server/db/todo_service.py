import aiosqlite
from server.config import settings

async def save_todos(session_id: str, todos: list):
    """Bulk insert todos for a session."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        for idx, todo in enumerate(todos):
            await db.execute('''
                INSERT INTO task_todos (session_id, position, title, tool_hint, args_hint)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                session_id,
                idx,
                todo.get('title', ''),
                todo.get('tool_hint'),
                todo.get('args_hint')
            ))
        await db.commit()

async def get_todos(session_id: str):
    """Get all todos for a session ordered by position."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT * FROM task_todos
            WHERE session_id = ?
            ORDER BY position
        ''', (session_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def update_todo_status(todo_id: int, status: str, error: str = None):
    """Update the status of a todo."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        if status == 'active':
            await db.execute('''
                UPDATE task_todos
                SET status = ?, started_at = datetime('now')
                WHERE id = ?
            ''', (status, todo_id))
        elif status == 'done':
            await db.execute('''
                UPDATE task_todos
                SET status = ?, completed_at = datetime('now')
                WHERE id = ?
            ''', (status, todo_id))
        elif status == 'failed':
            await db.execute('''
                UPDATE task_todos
                SET status = ?, error = ?, completed_at = datetime('now')
                WHERE id = ?
            ''', (status, error, todo_id))
        else:
            await db.execute('''
                UPDATE task_todos
                SET status = ?
                WHERE id = ?
            ''', (status, todo_id))
        await db.commit()

async def append_todos(session_id: str, new_todos: list):
    """Append new todos to an existing session (for replanning)."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        # Get the max position
        async with db.execute('''
            SELECT MAX(position) FROM task_todos WHERE session_id = ?
        ''', (session_id,)) as cursor:
            result = await cursor.fetchone()
            max_position = result[0] if result[0] is not None else -1

        # Insert new todos
        for idx, todo in enumerate(new_todos):
            await db.execute('''
                INSERT INTO task_todos (session_id, position, title, tool_hint, args_hint)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                session_id,
                max_position + idx + 1,
                todo.get('title', ''),
                todo.get('tool_hint'),
                todo.get('args_hint')
            ))
        await db.commit()

async def get_remaining_todos(session_id: str):
    """Get todos that are pending or active."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT * FROM task_todos
            WHERE session_id = ? AND status IN ('pending', 'active')
            ORDER BY position
        ''', (session_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def clear_todos(session_id: str):
    """Clear all todos for a session."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute('DELETE FROM task_todos WHERE session_id = ?', (session_id,))
        await db.commit()
