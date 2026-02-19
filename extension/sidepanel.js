// BrowserAgent Side Panel Script
// Handles UI, WebSocket communication, and user interactions

let port = null;
let sessionId = null;
let serverUrl = 'http://localhost:8000';
let currentAgentId = null;
let askMode = false;
let currentAssistantBubble = null;
let wsConnected = false;
let wsRetries = 0;
const MAX_WS_RETRIES = 5;

// DOM elements
const statusDot = document.getElementById('status-dot');
const agentStrip = document.getElementById('agent-strip');
const planPanel = document.getElementById('plan-panel');
const todoList = document.getElementById('todo-list');
const planActions = document.getElementById('plan-actions');
const approvePlanBtn = document.getElementById('approve-plan-btn');
const editPlanBtn = document.getElementById('edit-plan-btn');
const collapsePlanBtn = document.getElementById('collapse-plan-btn');
const activityBar = document.getElementById('activity-bar');
const activityText = document.getElementById('activity-text');
const chatArea = document.getElementById('chat-area');
const promptInput = document.getElementById('prompt-input');
const sendBtn = document.getElementById('send-btn');
const clearBtn = document.getElementById('clear-btn');
const askModeToggle = document.getElementById('ask-mode-toggle');
const confirmModal = document.getElementById('confirm-modal');
const confirmDescription = document.getElementById('confirm-description');
const confirmAllowBtn = document.getElementById('confirm-allow-btn');
const confirmDenyBtn = document.getElementById('confirm-deny-btn');

// Initialize
async function init() {
  // Get session ID
  const result = await chrome.storage.session.get(['sessionId']);
  sessionId = result.sessionId;

  // Get server URL
  const urlResult = await chrome.storage.local.get(['serverUrl']);
  if (urlResult.serverUrl) {
    serverUrl = urlResult.serverUrl;
  }

  // Get ask mode preference
  const modeResult = await chrome.storage.local.get(['askMode']);
  askMode = modeResult.askMode || false;
  askModeToggle.checked = askMode;

  // Connect to background script
  connectToBackground();

  // Load agents
  await loadAgents();

  // Load previous messages
  await loadMessages();

  // Setup event listeners
  setupEventListeners();
}

// Connect to background script via port
function connectToBackground() {
  port = chrome.runtime.connect({ name: 'sidepanel' });

  port.onMessage.addListener((msg) => {
    handleMessage(msg);
  });

  port.onDisconnect.addListener(() => {
    console.log('Port disconnected');
    statusDot.className = 'status-dot disconnected';
  });
}

// Handle messages from background
function handleMessage(msg) {
  console.log('Sidepanel received:', msg.type);

  switch (msg.type) {
    case 'ws_status':
      updateConnectionStatus(msg);
      break;
    case 'plan':
      renderPlan(msg.todos);
      break;
    case 'todo_update':
      updateTodo(msg.todo_id, msg.status);
      break;
    case 'token':
      appendToken(msg.content);
      break;
    case 'done':
      finalizeBubble();
      break;
    case 'confirm_action':
      showConfirmModal(msg.description);
      break;
    case 'error':
      appendToken(msg.content);
      finalizeBubble();
      break;
  }
}

// Update connection status
function updateConnectionStatus(data) {
  if (data.connected) {
    wsConnected = true;
    wsRetries = 0;
    statusDot.className = 'status-dot connected';
    statusDot.title = 'Connected';
    // Remove reconnect button if present
    const btn = document.getElementById('reconnect-btn');
    if (btn) btn.remove();
  } else if (data.retrying) {
    wsConnected = false;
    statusDot.className = 'status-dot reconnecting';
    statusDot.title = `Reconnecting... (attempt ${data.attempt}/${MAX_WS_RETRIES})`;
  } else {
    wsConnected = false;
    wsRetries++;
    statusDot.className = 'status-dot disconnected';
    statusDot.title = 'Disconnected — server offline?';
    if (wsRetries >= MAX_WS_RETRIES && !document.getElementById('reconnect-btn')) {
      const reconnectBtn = document.createElement('button');
      reconnectBtn.id = 'reconnect-btn';
      reconnectBtn.className = 'btn btn-secondary';
      reconnectBtn.style.cssText = 'margin: 8px 16px; width: calc(100% - 32px); font-size: 12px;';
      reconnectBtn.textContent = '🔄 Server offline — click to retry';
      reconnectBtn.onclick = () => {
        wsRetries = 0;
        reconnectBtn.remove();
        port.disconnect();
        connectToBackground();
      };
      chatArea.parentNode.insertBefore(reconnectBtn, chatArea);
    }
  }
}

// Load agents from server
async function loadAgents() {
  try {
    const response = await fetch(`${serverUrl}/api/v1/agents`);
    const agents = await response.json();

    agentStrip.innerHTML = '';

    agents.forEach(agent => {
      const pill = document.createElement('div');
      pill.className = 'agent-pill';
      pill.textContent = agent.name;
      pill.dataset.agentId = agent.id;

      pill.addEventListener('click', () => {
        // Toggle selection
        document.querySelectorAll('.agent-pill').forEach(p => p.classList.remove('active'));
        if (currentAgentId === agent.id) {
          currentAgentId = null;
        } else {
          pill.classList.add('active');
          currentAgentId = agent.id;
        }
      });

      agentStrip.appendChild(pill);
    });
  } catch (error) {
    console.error('Error loading agents:', error);
  }
}

// Load previous messages
async function loadMessages() {
  try {
    const response = await fetch(`${serverUrl}/api/v1/sessions/${sessionId}/messages`);
    const messages = await response.json();

    // Clear welcome message
    chatArea.innerHTML = '';

    messages.forEach(msg => {
      if (msg.role === 'user') {
        addUserMessage(msg.content);
      } else if (msg.role === 'assistant') {
        addAssistantMessage(msg.content);
      }
    });

    scrollToBottom();
  } catch (error) {
    console.error('Error loading messages:', error);
  }
}

// Render plan
function renderPlan(todos) {
  planPanel.style.display = 'block';
  todoList.innerHTML = '';

  todos.forEach((todo, index) => {
    const li = document.createElement('li');
    li.className = 'todo-item';
    li.id = `todo-${todo.id || index + 1}`;

    const icon = document.createElement('div');
    icon.className = 'todo-icon pending';

    const title = document.createElement('span');
    title.className = 'todo-title';
    title.textContent = todo.title;

    li.appendChild(icon);
    li.appendChild(title);
    todoList.appendChild(li);
  });

  // Show approval buttons if in ask mode
  if (askMode) {
    planActions.style.display = 'flex';
  } else {
    planActions.style.display = 'none';
    // Auto-approve after 2 seconds
    setTimeout(() => {
      if (port) {
        port.postMessage({ type: 'plan_approved' });
      }
    }, 2000);
  }
}

// Update todo status
function updateTodo(todoId, status) {
  const todoItem = document.getElementById(`todo-${todoId}`);
  if (!todoItem) return;

  const icon = todoItem.querySelector('.todo-icon');
  icon.className = `todo-icon ${status}`;

  if (status === 'done') {
    // Check if all todos are done
    const allTodos = todoList.querySelectorAll('.todo-item');
    const allDone = Array.from(allTodos).every(item => {
      const icon = item.querySelector('.todo-icon');
      return icon.classList.contains('done');
    });

    if (allDone) {
      // Collapse plan panel after a delay
      setTimeout(() => {
        collapsePlan();
      }, 1000);
    }
  }
}

// Collapse plan panel
function collapsePlan() {
  const allTodos = todoList.querySelectorAll('.todo-item');
  const doneCount = Array.from(allTodos).filter(item => {
    const icon = item.querySelector('.todo-icon');
    return icon.classList.contains('done');
  }).length;

  planPanel.innerHTML = `
    <div style="padding: 12px; cursor: pointer;" onclick="document.getElementById('plan-panel').style.display='none'">
      <span style="color: #22C55E;">✓</span> Plan: ${doneCount}/${allTodos.length} steps completed
    </div>
  `;
}

// Send message
async function sendMessage() {
  const content = promptInput.value.trim();
  if (!content) return;

  // Add user message to chat
  addUserMessage(content);

  // Clear input
  promptInput.value = '';

  // Get current tab URL
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  const tabUrl = tabs.length > 0 ? tabs[0].url : '';

  // Send to background
  if (port) {
    port.postMessage({
      type: 'user_message',
      content: content,
      agentId: currentAgentId,
      tabUrl: tabUrl,
      askMode: askMode
    });
  }

  // Create assistant bubble
  createAssistantBubble();
}

// Add user message
function addUserMessage(content) {
  const msg = document.createElement('div');
  msg.className = 'message user';

  const avatar = document.createElement('div');
  avatar.className = 'message-avatar';
  avatar.textContent = '👤';

  const msgContent = document.createElement('div');
  msgContent.className = 'message-content';
  msgContent.textContent = content;

  msg.appendChild(avatar);
  msg.appendChild(msgContent);

  chatArea.appendChild(msg);
  scrollToBottom();
}

// Create assistant bubble
function createAssistantBubble() {
  const msg = document.createElement('div');
  msg.className = 'message';

  const avatar = document.createElement('div');
  avatar.className = 'message-avatar';
  avatar.textContent = '🤖';

  const msgContent = document.createElement('div');
  msgContent.className = 'message-content';
  msgContent.textContent = '';

  msg.appendChild(avatar);
  msg.appendChild(msgContent);

  chatArea.appendChild(msg);
  currentAssistantBubble = msgContent;
  scrollToBottom();
}

// Add assistant message
function addAssistantMessage(content) {
  const msg = document.createElement('div');
  msg.className = 'message';

  const avatar = document.createElement('div');
  avatar.className = 'message-avatar';
  avatar.textContent = '🤖';

  const msgContent = document.createElement('div');
  msgContent.className = 'message-content';
  msgContent.textContent = content;

  msg.appendChild(avatar);
  msg.appendChild(msgContent);

  chatArea.appendChild(msg);
  scrollToBottom();
}

// Append token to current bubble
function appendToken(token) {
  if (currentAssistantBubble) {
    currentAssistantBubble.textContent += token;
    scrollToBottom();
  }
}

// Finalize bubble
function finalizeBubble() {
  currentAssistantBubble = null;
  activityBar.style.display = 'none';
}

// Show confirmation modal
function showConfirmModal(description) {
  confirmDescription.textContent = description;
  confirmModal.style.display = 'flex';
}

// Hide confirmation modal
function hideConfirmModal() {
  confirmModal.style.display = 'none';
}

// Clear chat
async function clearChat() {
  try {
    await fetch(`${serverUrl}/api/v1/sessions/${sessionId}`, {
      method: 'DELETE'
    });

    // Reset UI
    chatArea.innerHTML = '<div class="welcome-message"><h2>Welcome to BrowserAgent</h2><p>Select an agent above or let the orchestrator choose the best one for your task.</p></div>';
    planPanel.style.display = 'none';
    currentAgentId = null;
    document.querySelectorAll('.agent-pill').forEach(p => p.classList.remove('active'));

    // Generate new session ID
    sessionId = crypto.randomUUID();
    await chrome.storage.session.set({ sessionId });
  } catch (error) {
    console.error('Error clearing chat:', error);
  }
}

// Scroll to bottom
function scrollToBottom() {
  chatArea.scrollTop = chatArea.scrollHeight;
}

// Setup event listeners
function setupEventListeners() {
  sendBtn.addEventListener('click', sendMessage);

  promptInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  clearBtn.addEventListener('click', clearChat);

  askModeToggle.addEventListener('change', async (e) => {
    askMode = e.target.checked;
    await chrome.storage.local.set({ askMode });
  });

  approvePlanBtn.addEventListener('click', () => {
    planActions.style.display = 'none';
    if (port) {
      port.postMessage({ type: 'plan_approved' });
    }
  });

  editPlanBtn.addEventListener('click', () => {
    // Toggle edit mode
    const isEditing = editPlanBtn.dataset.editing === 'true';
    if (!isEditing) {
      // Enter edit mode: convert titles to inputs
      editPlanBtn.dataset.editing = 'true';
      editPlanBtn.textContent = 'Save Edits';
      todoList.querySelectorAll('.todo-title').forEach(el => {
        const input = document.createElement('input');
        input.type = 'text';
        input.value = el.textContent;
        input.className = 'todo-edit-input';
        input.style.cssText = `
          background: #0F172A;
          border: 1px solid #F97316;
          border-radius: 4px;
          color: #E2E8F0;
          font-size: 13px;
          padding: 2px 6px;
          width: 100%;
          flex: 1;
        `;
        el.replaceWith(input);
      });
    } else {
      // Save edits: collect modified todos
      editPlanBtn.dataset.editing = 'false';
      editPlanBtn.textContent = 'Edit Plan';
      const inputs = todoList.querySelectorAll('.todo-edit-input');
      const updatedTodos = Array.from(inputs).map((input, i) => {
        const span = document.createElement('span');
        span.className = 'todo-title';
        span.textContent = input.value;
        input.replaceWith(span);
        return { title: input.value, order: i + 1 };
      });
      // Send updated todos to server via port
      if (port) {
        port.postMessage({ type: 'plan_edited', todos: updatedTodos });
      }
      // Hide action bar and approve
      planActions.style.display = 'none';
    }
  });

  confirmAllowBtn.addEventListener('click', () => {
    if (port) {
      port.postMessage({ type: 'confirm_response', approved: true });
    }
    hideConfirmModal();
  });

  confirmDenyBtn.addEventListener('click', () => {
    if (port) {
      port.postMessage({ type: 'confirm_response', approved: false });
    }
    hideConfirmModal();
  });

  collapsePlanBtn.addEventListener('click', () => {
    planPanel.style.display = 'none';
  });
}

// Initialize on load
init();
