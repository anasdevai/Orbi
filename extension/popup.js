// BrowserAgent Popup Script

const serverUrlInput = document.getElementById('server-url');
const testBtn = document.getElementById('test-btn');
const saveBtn = document.getElementById('save-btn');
const openAgentsBtn = document.getElementById('open-agents-btn');
const statusDiv = document.getElementById('status');
const sessionIdSpan = document.getElementById('session-id');

// Load settings on init
async function init() {
  // Load server URL
  const result = await chrome.storage.local.get(['serverUrl']);
  if (result.serverUrl) {
    serverUrlInput.value = result.serverUrl;
  } else {
    serverUrlInput.value = 'http://localhost:8001';
  }

  // Load session ID
  const sessionResult = await chrome.storage.session.get(['sessionId']);
  if (sessionResult.sessionId) {
    sessionIdSpan.textContent = sessionResult.sessionId;
  }
}

// Test connection
async function testConnection() {
  const url = serverUrlInput.value.trim();
  if (!url) {
    showStatus('Please enter a server URL', 'error');
    return;
  }

  try {
    const response = await fetch(`${url}/api/v1/health`);
    const data = await response.json();

    if (data.status === 'ok') {
      showStatus(`✓ Connected (v${data.version})`, 'success');
    } else {
      showStatus('✗ Server responded but status not OK', 'error');
    }
  } catch (error) {
    showStatus('✗ Connection failed', 'error');
  }
}

// Save settings
async function saveSettings() {
  const url = serverUrlInput.value.trim();
  if (!url) {
    showStatus('Please enter a server URL', 'error');
    return;
  }

  await chrome.storage.local.set({ serverUrl: url });
  showStatus('✓ Settings saved', 'success');

  // Reload background script to reconnect with new URL
  setTimeout(() => {
    chrome.runtime.reload();
  }, 1000);
}

// Open agent manager
function openAgentManager() {
  chrome.tabs.create({ url: chrome.runtime.getURL('agents.html') });
}

// Show status message
function showStatus(message, type) {
  statusDiv.textContent = message;
  statusDiv.className = `status ${type}`;
  statusDiv.style.display = 'block';

  setTimeout(() => {
    statusDiv.style.display = 'none';
  }, 3000);
}

// Event listeners
testBtn.addEventListener('click', testConnection);
saveBtn.addEventListener('click', saveSettings);
openAgentsBtn.addEventListener('click', openAgentManager);

// Initialize
init();
