import aiosqlite
import uuid
import json
from server.config import settings

async def create_session(session_id: str, tab_url: str, agent_id: str = None, ask_mode: int = 0):
    """Create a new session."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute('''
            INSERT INTO sessions (id, tab_url, agent_id, ask_mode)
            VALUES (?, ?, ?, ?)
        ''', (session_id, tab_url, agent_id, ask_mode))
        await db.commit()

async def get_session(session_id: str):
    """Get a session by ID."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM sessions WHERE id = ?', (session_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def add_message(session_id: str, role: str, content: str, tool_calls: dict = None):
    """Add a message to a session."""
    message_id = str(uuid.uuid4())
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute('''
            INSERT INTO messages (id, session_id, role, content, tool_calls)
            VALUES (?, ?, ?, ?, ?)
        ''', (message_id, session_id, role, content, json.dumps(tool_calls) if tool_calls else None))
        await db.commit()
    return message_id

async def get_messages(session_id: str, limit: int = 20):
    """Get recent messages for a session."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT * FROM messages
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (session_id, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in reversed(rows)]

async def log_action(session_id: str, action_type: str, args: dict, result: str, success: bool, todo_id: int = None):
    """Log a browser action."""
    action_id = str(uuid.uuid4())
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute('''
            INSERT INTO browser_actions (id, session_id, todo_id, action_type, args, result, success)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (action_id, session_id, todo_id, action_type, json.dumps(args), result, int(success)))
        await db.commit()
    return action_id
