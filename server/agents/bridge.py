import asyncio
from fastapi import WebSocket
import json

class BrowserBridge:
    """Bridge between server and browser extension for tool calls and notifications."""

    def __init__(self):
        self.futures: dict[str, asyncio.Future] = {}
        self.websockets: dict[str, WebSocket] = {}
        self.confirm_futures: dict[str, asyncio.Future] = {}
        self.plan_futures: dict[str, asyncio.Future] = {}
        self.replan_counts: dict[str, int] = {}

    def register_session(self, session_id: str, ws: WebSocket):
        """Register a WebSocket connection for a session."""
        self.websockets[session_id] = ws

    def unregister_session(self, session_id: str):
        """Clean up all resources for a session."""
        self.websockets.pop(session_id, None)
        self.futures.pop(session_id, None)
        self.confirm_futures.pop(session_id, None)
        self.plan_futures.pop(session_id, None)
        self.replan_counts.pop(session_id, None)  # Reset replan count on disconnect

    async def send_tool_call(self, session_id: str, tool_name: str, args: dict) -> str:
        """Send a tool call to the browser and wait for result."""
        if session_id not in self.websockets:
            raise RuntimeError(f'No WebSocket connection for session {session_id}')

        # Create a future for this tool call
        future = asyncio.Future()
        self.futures[session_id] = future

        # Send tool call to extension
        ws = self.websockets[session_id]
        await ws.send_json({
            'type': 'tool_call',
            'tool': tool_name,
            'args': args
        })

        # Wait for result with timeout
        try:
            result = await asyncio.wait_for(future, timeout=30.0)
            return result
        except asyncio.TimeoutError:
            raise TimeoutError(f'Tool call {tool_name} timed out after 30 seconds')
        finally:
            self.futures.pop(session_id, None)

    def resolve_tool_call(self, session_id: str, result: str):
        """Resolve a pending tool call with its result."""
        if session_id in self.futures and not self.futures[session_id].done():
            self.futures[session_id].set_result(result)

    async def request_confirmation(self, session_id: str, description: str) -> bool:
        """Request user confirmation for a potentially destructive action."""
        if session_id not in self.websockets:
            return False

        # Create a future for this confirmation
        future = asyncio.Future()
        self.confirm_futures[session_id] = future

        # Send confirmation request
        ws = self.websockets[session_id]
        await ws.send_json({
            'type': 'confirm_action',
            'description': description
        })

        # Wait for user response with timeout
        try:
            approved = await asyncio.wait_for(future, timeout=60.0)
            return approved
        except asyncio.TimeoutError:
            return False  # Default to deny if no response
        finally:
            self.confirm_futures.pop(session_id, None)

    def resolve_confirmation(self, session_id: str, approved: bool):
        """Resolve a pending confirmation request."""
        if session_id in self.confirm_futures and not self.confirm_futures[session_id].done():
            self.confirm_futures[session_id].set_result(approved)

    async def notify_todo_update(self, session_id: str, todo_id: int, status: str):
        """Notify the UI about a todo status change."""
        if session_id in self.websockets:
            ws = self.websockets[session_id]
            try:
                await ws.send_json({
                    'type': 'todo_update',
                    'todo_id': todo_id,
                    'status': status
                })
            except Exception as e:
                print(f'Error sending todo update: {e}')

    async def notify_plan(self, session_id: str, todos: list):
        """Send the execution plan to the UI."""
        if session_id in self.websockets:
            ws = self.websockets[session_id]
            try:
                await ws.send_json({
                    'type': 'plan',
                    'todos': todos
                })
            except Exception as e:
                print(f'Error sending plan: {e}')

    async def wait_for_plan_approval(self, session_id: str) -> bool:
        """Wait for user to approve the plan (in Ask mode)."""
        # Create a future for plan approval
        future = asyncio.Future()
        self.plan_futures[session_id] = future

        # Wait for approval with timeout
        try:
            approved = await asyncio.wait_for(future, timeout=300.0)  # 5 minutes
            return approved
        except asyncio.TimeoutError:
            return False
        finally:
            self.plan_futures.pop(session_id, None)

    def resolve_plan_approval(self, session_id: str, approved: bool):
        """Resolve a pending plan approval."""
        if session_id in self.plan_futures and not self.plan_futures[session_id].done():
            self.plan_futures[session_id].set_result(approved)

# Global bridge instance
bridge = BrowserBridge()
