from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import aiosqlite
import uuid
from datetime import datetime
from server.config import settings

router = APIRouter()

class ScheduledTaskCreate(BaseModel):
    agent_id: str
    prompt: str
    cron_expr: str
    label: Optional[str] = None

class ScheduledTaskUpdate(BaseModel):
    prompt: Optional[str] = None
    cron_expr: Optional[str] = None
    label: Optional[str] = None
    is_active: Optional[int] = None

@router.get('/scheduled-tasks')
async def list_scheduled_tasks():
    """List all scheduled tasks."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM scheduled_tasks ORDER BY created_at DESC') as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

@router.post('/scheduled-tasks')
async def create_scheduled_task(task: ScheduledTaskCreate):
    """Create a new scheduled task."""
    # Validate cron expression
    try:
        from croniter import croniter
        if not croniter.is_valid(task.cron_expr):
            raise ValueError('Invalid cron expression')
        # Calculate initial next_run
        iter = croniter(task.cron_expr, datetime.now())
        next_run = iter.get_next(datetime).isoformat()
    except ImportError:
        next_run = None  # croniter not installed, worker will handle

    task_id = str(uuid.uuid4())
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute(
            '''INSERT INTO scheduled_tasks (id, agent_id, prompt, cron_expr, label, next_run, is_active, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 1, ?)''',
            (task_id, task.agent_id, task.prompt, task.cron_expr, task.label or task.prompt[:50], next_run, datetime.now().isoformat())
        )
        await db.commit()
    return {'id': task_id, 'next_run': next_run}

@router.patch('/scheduled-tasks/{task_id}')
async def update_scheduled_task(task_id: str, task: ScheduledTaskUpdate):
    """Update a scheduled task."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        updates = {k: v for k, v in task.dict().items() if v is not None}
        if not updates:
            raise HTTPException(status_code=400, detail='No fields to update')
        set_clause = ', '.join(f'{k} = ?' for k in updates)
        await db.execute(
            f'UPDATE scheduled_tasks SET {set_clause} WHERE id = ?',
            (*updates.values(), task_id)
        )
        await db.commit()
    return {'message': 'Updated successfully'}

@router.delete('/scheduled-tasks/{task_id}')
async def delete_scheduled_task(task_id: str):
    """Delete a scheduled task."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute('DELETE FROM scheduled_tasks WHERE id = ?', (task_id,))
        await db.commit()
    return {'message': 'Deleted successfully'}
