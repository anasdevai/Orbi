import aiosqlite
from server.config import settings

async def init_db():
    """Initialize the SQLite database with all required tables."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        # Table 1: agents
        await db.execute('''
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                system_prompt TEXT NOT NULL,
                model TEXT,
                allowed_tools TEXT DEFAULT '[]',
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        ''')

        # Table 2: sessions
        await db.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                tab_url TEXT,
                agent_id TEXT,
                ask_mode INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        ''')

        # Table 3: task_todos
        await db.execute('''
            CREATE TABLE IF NOT EXISTS task_todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                position INTEGER NOT NULL,
                title TEXT NOT NULL,
                tool_hint TEXT,
                args_hint TEXT,
                status TEXT DEFAULT 'pending',
                started_at TEXT,
                completed_at TEXT,
                error TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        ''')

        # Table 4: messages
        await db.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                content TEXT,
                tool_calls TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        ''')

        # Table 5: browser_actions
        await db.execute('''
            CREATE TABLE IF NOT EXISTS browser_actions (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                todo_id INTEGER,
                action_type TEXT NOT NULL,
                args TEXT,
                result TEXT,
                success INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        ''')

        # Table 6: scheduled_tasks
        await db.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id TEXT PRIMARY KEY,
                agent_id TEXT,
                cron_expr TEXT NOT NULL,
                prompt TEXT NOT NULL,
                last_run TEXT,
                next_run TEXT,
                is_active INTEGER DEFAULT 1
            )
        ''')

        await db.commit()
