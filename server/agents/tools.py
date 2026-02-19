from agents import function_tool
import re
import json
from server.agents.bridge import bridge
from server.db.session_service import log_action
from server.db.todo_service import update_todo_status, get_remaining_todos, append_todos
from server.agents.planner import replan as replan_module
from server.config import settings

# Validation constants
SAFE_REF_REGEX = re.compile(r'^a[0-9]+$')
BLOCKED_PATTERNS = [
    'javascript:', 'eval(', 'fetch(', 'XMLHttpRequest',
    'document.cookie', '<script', 'file://', 'data:'
]
DELETE_LABELS = [
    'delete', 'remove', 'unsubscribe', 'deactivate',
    'cancel account', 'clear all', 'erase', 'discard', 'revoke'
]

def validate_ref(ref_id: str) -> bool:
    """Validate that a ref ID is safe."""
    return bool(SAFE_REF_REGEX.match(ref_id))

def contains_blocked_pattern(text: str) -> bool:
    """Check if text contains any blocked patterns."""
    text_lower = text.lower()
    return any(pattern.lower() in text_lower for pattern in BLOCKED_PATTERNS)

# ============================================================================
# BROWSER TOOLS (20 tools)
# ============================================================================

@function_tool
async def read_page(session_id: str) -> str:
    """Read the accessibility tree of the current page. Returns interactive elements with ref IDs."""
    result = await bridge.send_tool_call(session_id, 'read_page', {})
    await log_action(session_id, 'read_page', {}, result, True)
    return result

@function_tool
async def get_page_text(session_id: str) -> str:
    """Get the raw visible text content of the current page."""
    result = await bridge.send_tool_call(session_id, 'get_page_text', {})
    await log_action(session_id, 'get_page_text', {}, result, True)
    return result

@function_tool
async def screenshot(session_id: str) -> str:
    """Take a screenshot of the visible tab area. Returns base64 JPEG."""
    result = await bridge.send_tool_call(session_id, 'screenshot', {})
    await log_action(session_id, 'screenshot', {}, 'Screenshot captured', True)
    return result

@function_tool
async def click_element(session_id: str, ref_id: str, label: str = '') -> str:
    """Click an element by its ref ID. Autonomous except for DELETE-class labels."""
    if not validate_ref(ref_id):
        return f'Error: Invalid ref_id format: {ref_id}'

    # Check if this is a DELETE-class action
    label_lower = label.lower()
    is_delete_action = any(delete_word in label_lower for delete_word in DELETE_LABELS)

    if is_delete_action:
        # Request confirmation
        approved = await bridge.request_confirmation(
            session_id,
            f'Click button: "{label}"'
        )
        if not approved:
            await log_action(session_id, 'click_element', {'ref_id': ref_id, 'label': label}, 'User denied', False)
            return 'Action cancelled by user'

    result = await bridge.send_tool_call(session_id, 'click_element', {'ref_id': ref_id})
    await log_action(session_id, 'click_element', {'ref_id': ref_id, 'label': label}, result, True)
    return result

@function_tool
async def type_text(session_id: str, ref_id: str, text: str) -> str:
    """Type text into an input field by ref ID. Always autonomous."""
    if not validate_ref(ref_id):
        return f'Error: Invalid ref_id format: {ref_id}'

    result = await bridge.send_tool_call(session_id, 'type_text', {'ref_id': ref_id, 'text': text})
    await log_action(session_id, 'type_text', {'ref_id': ref_id, 'text': text[:50]}, result, True)
    return result

@function_tool
async def select_option(session_id: str, ref_id: str, value: str) -> str:
    """Select an option in a dropdown by ref ID. Always autonomous."""
    if not validate_ref(ref_id):
        return f'Error: Invalid ref_id format: {ref_id}'

    result = await bridge.send_tool_call(session_id, 'select_option', {'ref_id': ref_id, 'value': value})
    await log_action(session_id, 'select_option', {'ref_id': ref_id, 'value': value}, result, True)
    return result

@function_tool
async def check_element(session_id: str, ref_id: str, checked: bool) -> str:
    """Check or uncheck a checkbox/radio by ref ID. Always autonomous."""
    if not validate_ref(ref_id):
        return f'Error: Invalid ref_id format: {ref_id}'

    result = await bridge.send_tool_call(session_id, 'check_element', {'ref_id': ref_id, 'checked': checked})
    await log_action(session_id, 'check_element', {'ref_id': ref_id, 'checked': checked}, result, True)
    return result

@function_tool
async def hover_element(session_id: str, ref_id: str) -> str:
    """Hover over an element by ref ID. Always autonomous."""
    if not validate_ref(ref_id):
        return f'Error: Invalid ref_id format: {ref_id}'

    result = await bridge.send_tool_call(session_id, 'hover_element', {'ref_id': ref_id})
    await log_action(session_id, 'hover_element', {'ref_id': ref_id}, result, True)
    return result

@function_tool
async def upload_file(session_id: str, ref_id: str, file_path: str) -> str:
    """Upload a file to an input. Always requires confirmation."""
    if not validate_ref(ref_id):
        return f'Error: Invalid ref_id format: {ref_id}'

    # Always confirm file uploads
    approved = await bridge.request_confirmation(
        session_id,
        f'Upload file: {file_path}'
    )
    if not approved:
        await log_action(session_id, 'upload_file', {'ref_id': ref_id, 'file_path': file_path}, 'User denied', False)
        return 'Upload cancelled by user'

    result = await bridge.send_tool_call(session_id, 'upload_file', {'ref_id': ref_id, 'file_path': file_path})
    await log_action(session_id, 'upload_file', {'ref_id': ref_id, 'file_path': file_path}, result, True)
    return result

@function_tool
async def scroll_page(session_id: str, direction: str = 'down', pixels: int = 300) -> str:
    """Scroll the page up or down. Always autonomous."""
    result = await bridge.send_tool_call(session_id, 'scroll_page', {'direction': direction, 'pixels': pixels})
    await log_action(session_id, 'scroll_page', {'direction': direction, 'pixels': pixels}, result, True)
    return result

@function_tool
async def navigate_to(session_id: str, url: str, current_domain: str = '') -> str:
    """Navigate to a URL. Autonomous for same domain, confirms for cross-domain."""
    # Block dangerous schemes
    if contains_blocked_pattern(url):
        return f'Error: Blocked URL pattern detected in {url}'

    # Check if cross-domain
    if current_domain:
        from urllib.parse import urlparse
        current_parsed = urlparse(current_domain)
        new_parsed = urlparse(url)

        if current_parsed.netloc and new_parsed.netloc and current_parsed.netloc != new_parsed.netloc:
            # Cross-domain navigation - request confirmation
            approved = await bridge.request_confirmation(
                session_id,
                f'Navigate to different site: {url}'
            )
            if not approved:
                await log_action(session_id, 'navigate_to', {'url': url}, 'User denied', False)
                return 'Navigation cancelled by user'

    result = await bridge.send_tool_call(session_id, 'navigate_to', {'url': url})
    await log_action(session_id, 'navigate_to', {'url': url}, result, True)
    return result

@function_tool
async def go_back(session_id: str) -> str:
    """Go back to the previous page. Always autonomous."""
    result = await bridge.send_tool_call(session_id, 'go_back', {})
    await log_action(session_id, 'go_back', {}, result, True)
    return result

@function_tool
async def get_tabs_context(session_id: str) -> str:
    """Get information about all open tabs."""
    result = await bridge.send_tool_call(session_id, 'get_tabs_context', {})
    await log_action(session_id, 'get_tabs_context', {}, result, True)
    return result

@function_tool
async def open_new_tab(session_id: str, url: str = '') -> str:
    """Open a new tab, optionally with a URL."""
    result = await bridge.send_tool_call(session_id, 'open_new_tab', {'url': url})
    await log_action(session_id, 'open_new_tab', {'url': url}, result, True)
    return result

@function_tool
async def close_tab(session_id: str, tab_id: int) -> str:
    """Close a tab by ID."""
    result = await bridge.send_tool_call(session_id, 'close_tab', {'tab_id': tab_id})
    await log_action(session_id, 'close_tab', {'tab_id': tab_id}, result, True)
    return result

@function_tool
async def switch_to_tab(session_id: str, tab_id: int) -> str:
    """Switch to a different tab by ID."""
    result = await bridge.send_tool_call(session_id, 'switch_to_tab', {'tab_id': tab_id})
    await log_action(session_id, 'switch_to_tab', {'tab_id': tab_id}, result, True)
    return result

@function_tool
async def javascript_tool(session_id: str, code: str) -> str:
    """Execute JavaScript in page context. Always requires confirmation. Disabled by default."""
    # Check for blocked patterns
    if contains_blocked_pattern(code):
        return f'Error: Blocked pattern detected in JavaScript code'

    # Always confirm JavaScript execution
    approved = await bridge.request_confirmation(
        session_id,
        f'Execute JavaScript: {code[:100]}...'
    )
    if not approved:
        await log_action(session_id, 'javascript_tool', {'code': code[:100]}, 'User denied', False)
        return 'JavaScript execution cancelled by user'

    result = await bridge.send_tool_call(session_id, 'javascript_tool', {'code': code})
    await log_action(session_id, 'javascript_tool', {'code': code[:100]}, result, True)
    return result

@function_tool
async def read_console(session_id: str) -> str:
    """Read browser console logs. May expose sensitive values."""
    result = await bridge.send_tool_call(session_id, 'read_console', {})
    await log_action(session_id, 'read_console', {}, result, True)
    return result

@function_tool
async def read_network(session_id: str) -> str:
    """Read network request log. Can expose OAuth tokens. Disabled by default."""
    result = await bridge.send_tool_call(session_id, 'read_network', {})
    await log_action(session_id, 'read_network', {}, result, True)
    return result

@function_tool
async def get_selected_text(session_id: str) -> str:
    """Get the currently selected/highlighted text on the page."""
    result = await bridge.send_tool_call(session_id, 'get_selected_text', {})
    await log_action(session_id, 'get_selected_text', {}, result, True)
    return result

# ============================================================================
# PLANNING TOOLS (2 tools - always injected)
# ============================================================================

@function_tool
async def mark_todo_done(session_id: str, todo_id: int) -> str:
    """Mark a todo step as completed. MUST be called after each step."""
    await update_todo_status(todo_id, 'done')
    await bridge.notify_todo_update(session_id, todo_id, 'done')
    await log_action(session_id, 'mark_todo_done', {'todo_id': todo_id}, 'done', True, todo_id=todo_id)
    return f'Step {todo_id} completed successfully.'

@function_tool
async def replan(session_id: str, failed_todo_id: int, error: str) -> str:
    """Called when a step fails. Generates replacement steps and appends to todo list."""
    # Check replan limit
    count = bridge.replan_counts.get(session_id, 0)
    if count >= settings.MAX_REPLAN_ATTEMPTS:
        return 'Max replan attempts reached. Summarize what was accomplished and explain the failure to the user.'

    bridge.replan_counts[session_id] = count + 1

    # Mark the failed todo
    await update_todo_status(failed_todo_id, 'failed', error=error)
    await bridge.notify_todo_update(session_id, failed_todo_id, 'failed')

    # Get remaining todos
    remaining = await get_remaining_todos(session_id)

    # Get the failed todo title
    from server.db.todo_service import get_todos
    all_todos = await get_todos(session_id)
    failed_todo = next((t for t in all_todos if t['id'] == failed_todo_id), None)
    failed_title = failed_todo['title'] if failed_todo else 'Unknown step'

    # Generate new steps
    new_steps = await replan_module(
        failed_todo_title=failed_title,
        error_message=error,
        remaining_todos=remaining,
        user_message='',
        available_tools=[]
    )

    if new_steps:
        await append_todos(session_id, new_steps)
        await bridge.notify_plan(session_id, new_steps)

    return json.dumps(new_steps)

# ============================================================================
# TOOL REGISTRY
# ============================================================================

ALL_TOOLS = [
    # Browser tools
    read_page, get_page_text, screenshot,
    click_element, type_text, select_option, check_element, hover_element, upload_file,
    scroll_page, navigate_to, go_back,
    get_tabs_context, open_new_tab, close_tab, switch_to_tab,
    javascript_tool, read_console, read_network, get_selected_text,
    # Planning tools
    mark_todo_done, replan
]

# Build tool registry - FunctionTool objects have a 'name' attribute
TOOL_REGISTRY = {}
for tool in ALL_TOOLS:
    # Get the name from the tool's name attribute or function name
    if hasattr(tool, 'name'):
        tool_name = tool.name
    elif hasattr(tool, '__name__'):
        tool_name = tool.__name__
    elif hasattr(tool, 'function') and hasattr(tool.function, '__name__'):
        tool_name = tool.function.__name__
    else:
        continue
    TOOL_REGISTRY[tool_name] = tool

PLANNING_TOOLS = [mark_todo_done, replan]
