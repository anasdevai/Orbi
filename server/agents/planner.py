import httpx
import json
from server.config import settings

PLANNER_SYSTEM_PROMPT = '''You are a task planner for a browser automation agent.
Given a user request, break it into a minimal ordered list of ATOMIC steps.
Each step must be achievable with ONE tool call OR one reasoning action.

Rules:
- Maximum 12 steps. Be as concise as possible.
- Use specific, action-oriented titles: "Read page to find revenue table"
  NOT vague titles: "Analyze the page"
- tool_hint must be one of the available tool names, or null for reasoning steps.
- args_hint is a brief plain-English description of what args to use.

Respond ONLY with a valid JSON array. No preamble, no explanation, no markdown.
Format: [{"id":1,"title":"...","tool_hint":"...","args_hint":"..."}]'''

async def generate_plan(
    user_message: str,
    agent_name: str,
    agent_description: str,
    tab_url: str,
    available_tools: list
) -> list:
    """Generate an execution plan using the planner LLM."""

    user_prompt = f'''Agent: {agent_name} — {agent_description}
Available tools: {json.dumps(available_tools)}
Current page URL: {tab_url}
User request: {user_message}

Produce the execution plan as JSON array.'''

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f'{settings.OPENROUTER_BASE_URL}/chat/completions',
                headers={
                    'Authorization': f'Bearer {settings.OPENROUTER_API_KEY}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': settings.PLANNER_MODEL,
                    'max_tokens': 1000,
                    'temperature': 0.1,
                    'messages': [
                        {'role': 'system', 'content': PLANNER_SYSTEM_PROMPT},
                        {'role': 'user', 'content': user_prompt}
                    ]
                }
            )
            response.raise_for_status()

            result = response.json()
            content = result['choices'][0]['message']['content'].strip()

            # Remove markdown code blocks if present
            if content.startswith('```'):
                lines = content.split('\n')
                content = '\n'.join(lines[1:-1]) if len(lines) > 2 else content

            # Parse JSON
            try:
                plan = json.loads(content)
            except json.JSONDecodeError:
                # Retry with simplified prompt
                simplified_prompt = f'''The user wants: {user_message}
Create a simple 3-step plan as JSON array: [{{"id":1,"title":"...","tool_hint":"read_page","args_hint":"..."}}]'''

                response = await client.post(
                    f'{settings.OPENROUTER_BASE_URL}/chat/completions',
                    headers={
                        'Authorization': f'Bearer {settings.OPENROUTER_API_KEY}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': settings.PLANNER_MODEL,
                        'max_tokens': 500,
                        'temperature': 0.1,
                        'messages': [
                            {'role': 'system', 'content': 'Return only valid JSON array of steps.'},
                            {'role': 'user', 'content': simplified_prompt}
                        ]
                    }
                )
                content = response.json()['choices'][0]['message']['content'].strip()
                plan = json.loads(content)

            # Validate and truncate
            if not isinstance(plan, list):
                plan = []

            # Ensure each item has required fields
            validated_plan = []
            for item in plan[:settings.MAX_TODOS]:
                if isinstance(item, dict) and 'title' in item:
                    validated_plan.append({
                        'id': item.get('id', len(validated_plan) + 1),
                        'title': item['title'],
                        'tool_hint': item.get('tool_hint'),
                        'args_hint': item.get('args_hint')
                    })

            return validated_plan

    except Exception as e:
        print(f'Error generating plan: {e}')
        # Return a basic fallback plan
        return [
            {
                'id': 1,
                'title': 'Read the current page',
                'tool_hint': 'read_page',
                'args_hint': 'Get page content'
            },
            {
                'id': 2,
                'title': 'Analyze and respond to user request',
                'tool_hint': None,
                'args_hint': 'Process the information'
            }
        ]

async def replan(
    failed_todo_title: str,
    error_message: str,
    remaining_todos: list,
    user_message: str,
    available_tools: list
) -> list:
    """Generate replacement steps when a todo fails."""

    remaining_str = '\n'.join(f"{t['position']+1}. {t['title']}" for t in remaining_todos)

    user_prompt = f'''A step in the browser automation plan failed.

Failed step: {failed_todo_title}
Error: {error_message}

Remaining plan:
{remaining_str}

Original user request: {user_message}
Available tools: {json.dumps(available_tools)}

Generate replacement steps to recover and complete the original task.
Keep it minimal — 1 to 4 steps max.
Return ONLY a JSON array in the same format: [{{"id":1,"title":"...","tool_hint":"...","args_hint":"..."}}]'''

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f'{settings.OPENROUTER_BASE_URL}/chat/completions',
                headers={
                    'Authorization': f'Bearer {settings.OPENROUTER_API_KEY}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': settings.PLANNER_MODEL,
                    'max_tokens': 500,
                    'temperature': 0.2,
                    'messages': [
                        {'role': 'system', 'content': 'You are a recovery planner. Generate minimal replacement steps as JSON array.'},
                        {'role': 'user', 'content': user_prompt}
                    ]
                }
            )
            response.raise_for_status()

            content = response.json()['choices'][0]['message']['content'].strip()

            # Remove markdown if present
            if content.startswith('```'):
                lines = content.split('\n')
                content = '\n'.join(lines[1:-1]) if len(lines) > 2 else content

            new_steps = json.loads(content)

            if not isinstance(new_steps, list):
                return []

            # Validate
            validated_steps = []
            for item in new_steps[:4]:  # Max 4 recovery steps
                if isinstance(item, dict) and 'title' in item:
                    validated_steps.append({
                        'id': item.get('id', len(validated_steps) + 1),
                        'title': item['title'],
                        'tool_hint': item.get('tool_hint'),
                        'args_hint': item.get('args_hint')
                    })

            return validated_steps

    except Exception as e:
        print(f'Error replanning: {e}')
        return []
