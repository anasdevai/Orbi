// BrowserAgent Agent Manager Script

let serverUrl = 'http://localhost:8001';
let editingAgentId = null;

// Tool definitions grouped by category
const TOOL_GROUPS = {
  'Page Reading': ['read_page', 'get_page_text', 'screenshot', 'scroll_page'],
  'Interaction': ['click_element', 'type_text', 'select_option', 'check_element', 'hover_element', 'upload_file'],
  'Navigation': ['navigate_to', 'go_back'],
  'Tab Management': ['get_tabs_context', 'open_new_tab', 'close_tab', 'switch_to_tab'],
  'Dev Tools': ['read_console', 'read_network'],
  'Advanced': ['javascript_tool'],
  'Planning (Always Included)': ['mark_todo_done', 'replan']
};

// DOM elements
const agentGrid = document.getElementById('agent-grid');
const newAgentBtn = document.getElementById('new-agent-btn');
const agentModal = document.getElementById('agent-modal');
const modalTitle = document.getElementById('modal-title');
const agentNameInput = document.getElementById('agent-name');
const agentDescriptionInput = document.getElementById('agent-description');
const agentPromptInput = document.getElementById('agent-prompt');
const agentModelSelect = document.getElementById('agent-model');
const toolChecklist = document.getElementById('tool-checklist');
const saveAgentBtn = document.getElementById('save-agent-btn');
const cancelAgentBtn = document.getElementById('cancel-agent-btn');

// Initialize
async function init() {
  // Get server URL
  const result = await chrome.storage.local.get(['serverUrl']);
  if (result.serverUrl) {
    serverUrl = result.serverUrl;
  }

  // Build tool checklist
  buildToolChecklist();

  // Load agents
  await loadAgents();

  // Setup event listeners
  setupEventListeners();
}

// Build tool checklist
function buildToolChecklist() {
  toolChecklist.innerHTML = '';

  for (const [groupName, tools] of Object.entries(TOOL_GROUPS)) {
    const groupDiv = document.createElement('div');
    groupDiv.className = 'tool-group';

    const groupTitle = document.createElement('div');
    groupTitle.className = 'tool-group-title';
    groupTitle.textContent = groupName;
    groupDiv.appendChild(groupTitle);

    tools.forEach(tool => {
      const checkboxItem = document.createElement('div');
      checkboxItem.className = 'checkbox-item';

      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.id = `tool-${tool}`;
      checkbox.value = tool;

      // Planning tools are always checked and disabled
      if (groupName === 'Planning (Always Included)') {
        checkbox.checked = true;
        checkbox.disabled = true;
      }

      const label = document.createElement('label');
      label.htmlFor = `tool-${tool}`;
      label.textContent = tool;

      // Add warning badges for high-risk tools
      if (tool === 'javascript_tool') {
        const badge = document.createElement('span');
        badge.className = 'warning-badge';
        badge.textContent = 'HIGH RISK';
        label.appendChild(badge);
      } else if (tool === 'read_network') {
        const badge = document.createElement('span');
        badge.className = 'warning-badge';
        badge.textContent = 'SENSITIVE';
        label.appendChild(badge);
      }

      checkboxItem.appendChild(checkbox);
      checkboxItem.appendChild(label);
      groupDiv.appendChild(checkboxItem);
    });

    toolChecklist.appendChild(groupDiv);
  }
}

// Load agents from server
async function loadAgents() {
  try {
    const response = await fetch(`${serverUrl}/api/v1/agents`);
    const agents = await response.json();

    agentGrid.innerHTML = '';

    if (agents.length === 0) {
      agentGrid.innerHTML = '<p style="color: #64748B; text-align: center; padding: 40px;">No agents yet. Create your first agent!</p>';
      return;
    }

    agents.forEach(agent => {
      const card = createAgentCard(agent);
      agentGrid.appendChild(card);
    });
  } catch (error) {
    console.error('Error loading agents:', error);
    agentGrid.innerHTML = '<p style="color: #EF4444; text-align: center; padding: 40px;">Error loading agents. Is the server running?</p>';
  }
}

// Create agent card
function createAgentCard(agent) {
  const card = document.createElement('div');
  card.className = 'agent-card';

  const header = document.createElement('div');
  header.className = 'agent-card-header';

  const title = document.createElement('h3');
  title.textContent = agent.name;

  const actions = document.createElement('div');
  actions.className = 'agent-card-actions';

  const editBtn = document.createElement('button');
  editBtn.className = 'icon-btn';
  editBtn.textContent = '✏️';
  editBtn.title = 'Edit';
  editBtn.onclick = () => editAgent(agent);

  const deleteBtn = document.createElement('button');
  deleteBtn.className = 'icon-btn';
  deleteBtn.textContent = '🗑️';
  deleteBtn.title = 'Delete';
  deleteBtn.onclick = () => deleteAgent(agent.id, agent.name);

  actions.appendChild(editBtn);
  actions.appendChild(deleteBtn);

  header.appendChild(title);
  header.appendChild(actions);

  const description = document.createElement('div');
  description.className = 'agent-description';
  description.textContent = agent.description;

  const tools = document.createElement('div');
  tools.className = 'agent-tools';

  const allowedTools = JSON.parse(agent.allowed_tools || '[]');
  allowedTools.slice(0, 6).forEach(tool => {
    const badge = document.createElement('span');
    badge.className = 'tool-badge';
    badge.textContent = tool;
    tools.appendChild(badge);
  });

  if (allowedTools.length > 6) {
    const badge = document.createElement('span');
    badge.className = 'tool-badge';
    badge.textContent = `+${allowedTools.length - 6} more`;
    tools.appendChild(badge);
  }

  card.appendChild(header);
  card.appendChild(description);
  card.appendChild(tools);

  return card;
}

// Open new agent modal
function openNewAgentModal() {
  editingAgentId = null;
  modalTitle.textContent = 'New Agent';

  // Clear form
  agentNameInput.value = '';
  agentDescriptionInput.value = '';
  agentPromptInput.value = '';
  agentModelSelect.value = 'openai/gpt-4o';

  // Uncheck all tools except planning tools
  document.querySelectorAll('#tool-checklist input[type="checkbox"]').forEach(checkbox => {
    if (!checkbox.disabled) {
      checkbox.checked = false;
    }
  });

  agentModal.style.display = 'flex';
}

// Edit agent
function editAgent(agent) {
  editingAgentId = agent.id;
  modalTitle.textContent = 'Edit Agent';

  // Fill form
  agentNameInput.value = agent.name;
  agentDescriptionInput.value = agent.description;
  agentPromptInput.value = agent.system_prompt;
  agentModelSelect.value = agent.model;

  // Check appropriate tools
  const allowedTools = JSON.parse(agent.allowed_tools || '[]');
  document.querySelectorAll('#tool-checklist input[type="checkbox"]').forEach(checkbox => {
    if (!checkbox.disabled) {
      checkbox.checked = allowedTools.includes(checkbox.value);
    }
  });

  agentModal.style.display = 'flex';
}

// Save agent
async function saveAgent() {
  const name = agentNameInput.value.trim();
  const description = agentDescriptionInput.value.trim();
  const systemPrompt = agentPromptInput.value.trim();
  const model = agentModelSelect.value;

  if (!name || !description || !systemPrompt) {
    alert('Please fill in all required fields');
    return;
  }

  // Get selected tools
  const allowedTools = [];
  document.querySelectorAll('#tool-checklist input[type="checkbox"]:checked').forEach(checkbox => {
    if (!checkbox.disabled) {
      allowedTools.push(checkbox.value);
    }
  });

  const agentData = {
    name,
    description,
    system_prompt: systemPrompt,
    model,
    allowed_tools: allowedTools
  };

  try {
    let response;
    if (editingAgentId) {
      // Update existing agent
      response = await fetch(`${serverUrl}/api/v1/agents/${editingAgentId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(agentData)
      });
    } else {
      // Create new agent
      response = await fetch(`${serverUrl}/api/v1/agents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(agentData)
      });
    }

    if (response.ok) {
      closeModal();
      await loadAgents();
    } else {
      const error = await response.json();
      alert(`Error: ${error.detail || 'Failed to save agent'}`);
    }
  } catch (error) {
    console.error('Error saving agent:', error);
    alert('Error saving agent. Is the server running?');
  }
}

// Delete agent
async function deleteAgent(agentId, agentName) {
  if (!confirm(`Are you sure you want to delete "${agentName}"?`)) {
    return;
  }

  try {
    const response = await fetch(`${serverUrl}/api/v1/agents/${agentId}`, {
      method: 'DELETE'
    });

    if (response.ok) {
      await loadAgents();
    } else {
      const error = await response.json();
      alert(`Error: ${error.detail || 'Failed to delete agent'}`);
    }
  } catch (error) {
    console.error('Error deleting agent:', error);
    alert('Error deleting agent. Is the server running?');
  }
}

// Close modal
function closeModal() {
  agentModal.style.display = 'none';
  editingAgentId = null;
}

// Setup event listeners
function setupEventListeners() {
  newAgentBtn.addEventListener('click', openNewAgentModal);
  saveAgentBtn.addEventListener('click', saveAgent);
  cancelAgentBtn.addEventListener('click', closeModal);

  // Close modal on background click
  agentModal.addEventListener('click', (e) => {
    if (e.target === agentModal) {
      closeModal();
    }
  });
}

// Initialize on load
init();
