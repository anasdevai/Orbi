from fastapi import APIRouter, HTTPException
from server.db.session_service import get_session, get_messages
from server.db.todo_service import get_todos
import aiosqlite
from server.config import settings

router = APIRouter()

@router.get('/sessions/{session_id}/messages')
async def get_session_messages(session_id: str, limit: int = 20):
    """Get messages for a session."""
    messages = await get_messages(session_id, limit)
    return messages

@router.get('/sessions/{session_id}/todos')
async def get_session_todos(session_id: str):
    """Get todos for a session."""
    todos = await get_todos(session_id)
    return todos

@router.delete('/sessions/{session_id}')
async def delete_session(session_id: str):
    """Delete a session and all related data."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        # Delete session (cascade will handle related records)
        await db.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
        await db.commit()

    return {'message': 'Session deleted successfully'}
