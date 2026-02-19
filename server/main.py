from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from server.db.models import init_db
from server.db.agent_service import seed_default_agents
from server.routers import ws, agents, sessions
from server.routers import scheduled_tasks as sched_tasks
import aiosqlite
from server.config import settings

import asyncio
from datetime import datetime
from croniter import croniter
from server.db.agent_service import get_all_agents
from server.db.session_service import create_session
from server.agents.orchestrator import run_agent_task

async def scheduled_task_worker():
    """Background worker that executes scheduled tasks."""
    print("Scheduled task worker started")
    while True:
        try:
            async with aiosqlite.connect(settings.DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                now = datetime.now().isoformat()
                
                # Find due tasks
                async with db.execute(
                    'SELECT * FROM scheduled_tasks WHERE is_active = 1 AND (next_run IS NULL OR next_run <= ?)',
                    (now,)
                ) as cursor:
                    due_tasks = await cursor.fetchall()
                
                for task in due_tasks:
                    print(f"Executing scheduled task: {task['id']}")
                    
                    # Create a session for this task run
                    session_id = f"sched-{task['id']}-{int(datetime.now().timestamp())}"
                    await create_session(session_id, "scheduled-task", task['agent_id'], 0)
                    
                    # Run the task (fire and forget in this context)
                    asyncio.create_task(execute_task(session_id, task['prompt'], task['agent_id']))
                    
                    # Update next run time
                    iter = croniter(task['cron_expr'], datetime.now())
                    next_run = iter.get_next(datetime).isoformat()
                    
                    await db.execute(
                        'UPDATE scheduled_tasks SET last_run = ?, next_run = ? WHERE id = ?',
                        (now, next_run, task['id'])
                    )
                
                await db.commit()
        except Exception as e:
            print(f"Error in scheduled task worker: {e}")
        
        await asyncio.sleep(60)

async def execute_task(session_id: str, prompt: str, agent_id: str):
    """Helper to execute a task and consume the generator."""
    async for _ in run_agent_task(session_id, prompt, agent_id):
        pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup
    await init_db()
    await seed_default_agents()
    print('Database initialized and default agents seeded')
    
    # Start background worker
    worker_task = asyncio.create_task(scheduled_task_worker())
    
    yield
    # Shutdown
    worker_task.cancel()
    print('Shutting down...')

# Create FastAPI app
app = FastAPI(
    title='BrowserAgent API',
    version='3.0.0',
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={'error': str(exc)}
    )

# Include routers
app.include_router(ws.router)
app.include_router(agents.router, prefix='/api/v1')
app.include_router(sessions.router, prefix='/api/v1')
app.include_router(sched_tasks.router, prefix='/api/v1')

@app.get('/api/v1/health')
async def health_check():
    """Health check endpoint."""
    return {'status': 'ok', 'version': '3.0.0'}
