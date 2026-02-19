import aiosqlite
import uuid
import json
from server.config import settings

async def create_agent(name: str, description: str, system_prompt: str, model: str, allowed_tools: list) -> str:
    """Create a new agent and return its ID."""
    agent_id = str(uuid.uuid4())
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute('''
            INSERT INTO agents (id, name, description, system_prompt, model, allowed_tools)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (agent_id, name, description, system_prompt, model, json.dumps(allowed_tools)))
        await db.commit()
    return agent_id

async def get_all_agents():
    """Get all active agents."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM agents WHERE is_active = 1 ORDER BY created_at') as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_agent(agent_id: str):
    """Get a single agent by ID."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM agents WHERE id = ?', (agent_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def update_agent(agent_id: str, **fields):
    """Update agent fields."""
    if not fields:
        return

    # Convert allowed_tools to JSON if present
    if 'allowed_tools' in fields and isinstance(fields['allowed_tools'], list):
        fields['allowed_tools'] = json.dumps(fields['allowed_tools'])

    set_clause = ', '.join(f'{key} = ?' for key in fields.keys())
    values = list(fields.values()) + [agent_id]

    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute(f'UPDATE agents SET {set_clause} WHERE id = ?', values)
        await db.commit()

async def delete_agent(agent_id: str):
    """Soft delete an agent by setting is_active to 0."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute('UPDATE agents SET is_active = 0 WHERE id = ?', (agent_id,))
        await db.commit()

async def seed_default_agents():
    """Seed default agents if the agents table is empty."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        async with db.execute('SELECT COUNT(*) FROM agents') as cursor:
            count = (await cursor.fetchone())[0]

        if count > 0:
            return  # Already seeded

    # Agent 1: Sales Analyzer
    await create_agent(
        name='Sales Analyzer',
        description='Use me when you need to analyze sales data, revenue figures, KPIs, conversion rates, or charts on the current page',
        system_prompt='You are a sales data analyst. Read the current page and extract all revenue, sales, conversion, and growth metrics. Present findings as a markdown summary with a metrics table. Highlight the most important numbers.',
        model=settings.DEFAULT_MODEL,
        allowed_tools=['read_page', 'get_page_text', 'scroll_page', 'screenshot']
    )

    # Agent 2: Page Summarizer
    await create_agent(
        name='Page Summarizer',
        description='Use me to summarize any article, documentation page, blog post, or long text page into concise bullet points',
        system_prompt='Summarize the current page content as: 1 sentence TL;DR, then up to 5 key points as bullets, then any action items or next steps if present. Keep total response under 300 words.',
        model=settings.DEFAULT_MODEL,
        allowed_tools=['read_page', 'get_page_text', 'scroll_page']
    )

    # Agent 3: Form Filler
    await create_agent(
        name='Form Filler',
        description='Use me when the user needs to fill out a web form on the current page',
        system_prompt='You are a form-filling assistant. First read the page to identify all form fields. Tell the user what fields are available. Fill each field using type_text and select_option. ALWAYS call mark_todo_done after each field filled. ALWAYS ask for confirmation before clicking any submit button.',
        model=settings.DEFAULT_MODEL,
        allowed_tools=['read_page', 'click_element', 'type_text', 'select_option', 'check_element', 'scroll_page']
    )
