from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from server.agents.bridge import bridge
from server.agents.orchestrator import run_agent_task
from server.db.session_service import create_session
from server.db.todo_service import clear_todos, save_todos
import asyncio
import json

router = APIRouter()

@router.websocket('/ws/{session_id}')
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time communication with the extension."""
    await websocket.accept()
    bridge.register_session(session_id, websocket)

    try:
        while True:
            # Receive message from extension
            data = await websocket.receive_json()
            message_type = data.get('type')

            if message_type == 'user_message':
                # User sent a new message
                content = data.get('content', '')
                agent_id = data.get('agentId')
                tab_url = data.get('tabUrl', '')
                ask_mode = data.get('askMode', False)

                # Create session in database
                try:
                    await create_session(session_id, tab_url, agent_id, int(ask_mode))
                except Exception as e:
                    # Session might already exist, that's okay
                    print(f'Session creation note: {e}')

                # Start agent task in background
                async def stream_task():
                    try:
                        async for token in run_agent_task(
                            session_id=session_id,
                            user_message=content,
                            agent_id=agent_id,
                            tab_url=tab_url,
                            ask_mode=ask_mode
                        ):
                            await websocket.send_json({
                                'type': 'token',
                                'content': token
                            })

                        # Send done signal
                        await websocket.send_json({'type': 'done'})

                    except Exception as e:
                        print(f'Stream task error: {e}')
                        import traceback
                        traceback.print_exc()
                        await websocket.send_json({
                            'type': 'error',
                            'content': f'Error: {str(e)}'
                        })

                # Create task without awaiting
                asyncio.create_task(stream_task())

            elif message_type == 'tool_result':
                # Extension returned a tool result
                result = data.get('result', '')
                bridge.resolve_tool_call(session_id, result)

            elif message_type == 'confirm_response':
                # User responded to confirmation request
                approved = data.get('approved', False)
                bridge.resolve_confirmation(session_id, approved)

            elif message_type == 'plan_approved':
                # User approved the plan
                bridge.resolve_plan_approval(session_id, True)

            elif message_type == 'plan_edited':
                # User edited the plan
                new_todos = data.get('todos', [])
                await clear_todos(session_id)
                await save_todos(session_id, new_todos)
                bridge.resolve_plan_approval(session_id, True)

    except WebSocketDisconnect:
        print(f'WebSocket disconnected: {session_id}')
    except Exception as e:
        print(f'WebSocket error: {e}')
    finally:
        bridge.unregister_session(session_id)
