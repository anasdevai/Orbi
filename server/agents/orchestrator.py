from agents import Runner
from server.agents.planner import generate_plan
from server.agents.factory import build_agent, build_orchestrator
from server.agents.bridge import bridge
from server.db.agent_service import get_all_agents, get_agent
from server.db.session_service import add_message
from server.db.todo_service import save_todos, get_todos
import json
from typing import AsyncGenerator

def format_todos(todos: list) -> str:
    """Format todos as a readable list for the agent."""
    lines = []
    for todo in todos:
        status = todo.get('status', 'pending')
        position = todo.get('position', 0)
        title = todo.get('title', '')
        lines.append(f"{position + 1}. [{status}] {title}")
    return '\n'.join(lines)

async def run_agent_task(
    session_id: str,
    user_message: str,
    agent_id: str = None,
    tab_url: str = '',
    ask_mode: bool = False
) -> AsyncGenerator[str, None]:
    """
    Main orchestration function that implements the Plan-then-Execute pipeline.

    Steps:
    1. Load agent record
    2. Generate plan
    3. Save todos to DB
    4. Notify UI with plan
    5. Wait for approval (if ask_mode)
    6. Build agent with plan context
    7. Execute with streaming
    8. Save final message
    """
    try:
        # STEP 1: Load agent record
        if agent_id:
            record = await get_agent(agent_id)
            if not record:
                yield f'Error: Agent {agent_id} not found'
                return
        else:
            # Implement Orchestrator routing to pick the best sub-agent
            agents_records = await get_all_agents()
            if not agents_records:
                yield 'Error: No active agents available'
                return
            
            # Use a lightweight LLM call to pick the best agent
            agent_options = "\n".join([f"- {r['name']}: {r['description']}" for r in agents_records])
            routing_prompt = f"""Given the user request, identify which of the following specialized agents is best suited to handle it.
            
Available Agents:
{agent_options}

User Request: {user_message}

Respond ONLY with the EXACT name of the selected agent. No other text."""

            import httpx
            from server.config import settings
            
            yield "Routing to best sub-agent...\n"
            
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{settings.OPENROUTER_BASE_URL}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": settings.DEFAULT_MODEL,
                            "messages": [{"role": "user", "content": routing_prompt}],
                            "temperature": 0
                        }
                    )
                    response.raise_for_status()
                    routing_data = response.json()
                    selected_name = routing_data['choices'][0]['message']['content'].strip()
            except Exception as e:
                print(f"Routing error: {e}")
                selected_name = agents_records[0]['name']

            # Find the record by name
            record = agents_records[0]
            for r in agents_records:
                if r['name'].lower() in selected_name.lower():
                    record = r
                    break
            
            yield f"Selected agent: {record['name']}\n"

        # STEP 2: Generate plan
        allowed_tools = json.loads(record['allowed_tools']) if isinstance(record['allowed_tools'], str) else record['allowed_tools']

        plan = await generate_plan(
            user_message=user_message,
            agent_name=record['name'],
            agent_description=record['description'],
            tab_url=tab_url,
            available_tools=allowed_tools
        )

        if not plan:
            yield 'Error: Failed to generate execution plan'
            return

        # STEP 3: Save todos to database
        await save_todos(session_id, plan)

        # STEP 4: Notify UI with plan
        await bridge.notify_plan(session_id, plan)

        # STEP 5: Wait for approval if in ask mode
        if ask_mode:
            approved = await bridge.wait_for_plan_approval(session_id)
            if not approved:
                yield 'Plan cancelled by user.'
                return

        # STEP 6: Build agent with plan context
        agent = build_agent(record, session_id)

        # Format todos for agent context
        todos_str = format_todos(plan)
        input_with_plan = f'''{user_message}

Your execution plan (follow exactly):
{todos_str}'''

        # STEP 7: Execute agent with streaming
        full_response = []

        result = Runner.run_streamed(agent, input=input_with_plan)

        async for event in result.stream_events():
            if hasattr(event, 'delta') and event.delta:
                full_response.append(event.delta)
                yield event.delta

        # STEP 8: Save assistant message
        response_text = ''.join(full_response)
        await add_message(session_id, 'assistant', response_text)

    except Exception as e:
        error_msg = f'Error: {str(e)}'
        print(f'Error in run_agent_task: {e}')
        import traceback
        traceback.print_exc()
        yield error_msg
