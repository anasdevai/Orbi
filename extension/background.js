// BrowserAgent Background Service Worker
// Handles WebSocket connection, tool relay, and session management

let ws = null;
let sessionId = null;
let serverUrl = 'http://localhost:8000';
let activeTabId = null;
let sidepanelPort = null;
let retries = 0;
const MAX_RETRIES = 5;

// Initialize on load
chrome.runtime.onInstalled.addListener(async () => {
  console.log('BrowserAgent installed');
  await initializeSession();
});

chrome.runtime.onStartup.addListener(async () => {
  console.log('BrowserAgent starting up');
  await initializeSession();
});

// Initialize session and connect
async function initializeSession() {
  // Get or generate session ID
  const result = await chrome.storage.session.get(['sessionId']);
  if (result.sessionId) {
    sessionId = result.sessionId;
  } else {
    sessionId = crypto.randomUUID();
    await chrome.storage.session.set({ sessionId });
  }

  // Get server URL from storage
  const urlResult = await chrome.storage.local.get(['serverUrl']);
  if (urlResult.serverUrl) {
    serverUrl = urlResult.serverUrl;
  }

  console.log('Session ID:', sessionId);
  console.log('Server URL:', serverUrl);

  // Connect WebSocket
  connectWS();
}

// Connect to WebSocket server
function connectWS() {
  const wsUrl = serverUrl.replace('http', 'ws') + '/ws/' + sessionId;
  console.log('Connecting to:', wsUrl);

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log('WebSocket connected');
    retries = 0;
    if (sidepanelPort) {
      sidepanelPort.postMessage({ type: 'ws_status', connected: true });
    }
  };

  ws.onmessage = async (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data.type);

    if (data.type === 'tool_call') {
      // Handle tool call
      await handleToolCall(data.tool, data.args);
    } else {
      // Forward to sidepanel
      if (sidepanelPort) {
        sidepanelPort.postMessage(data);
      }
    }
  };

  ws.onclose = () => {
    console.log('WebSocket closed');
    retries++;
    if (retries <= MAX_RETRIES) {
      const delay = Math.pow(2, retries) * 1000;
      console.log(`Reconnecting in ${delay}ms (attempt ${retries}/${MAX_RETRIES})`);
      if (sidepanelPort) {
        sidepanelPort.postMessage({ type: 'ws_status', connected: false, retrying: true, attempt: retries });
      }
      setTimeout(connectWS, delay);
    } else {
      console.error('Max reconnection attempts reached');
      if (sidepanelPort) {
        sidepanelPort.postMessage({ type: 'ws_status', connected: false, retrying: false });
      }
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
  };
}

// Handle tool calls from server
async function handleToolCall(tool, args) {
  console.log('Tool call:', tool, args);

  try {
    let result;

    if (tool === 'screenshot') {
      // Handle screenshot in background
      result = await captureScreenshot();
    } else {
      // Send to content script
      result = await sendToContentScript(tool, args);
    }

    // Send result back to server
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'tool_result',
        result: result
      }));
    }
  } catch (error) {
    console.error('Tool call error:', error);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'tool_result',
        result: JSON.stringify({ success: false, error: error.message })
      }));
    }
  }
}

// Capture screenshot
async function captureScreenshot() {
  try {
    const dataUrl = await chrome.tabs.captureVisibleTab(null, {
      format: 'jpeg',
      quality: 50
    });
    return JSON.stringify({ success: true, result: dataUrl });
  } catch (error) {
    return JSON.stringify({ success: false, error: error.message });
  }
}

// Send message to content script
async function sendToContentScript(tool, args) {
  if (!activeTabId) {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tabs.length > 0) {
      activeTabId = tabs[0].id;
    }
  }

  if (!activeTabId) {
    return JSON.stringify({ success: false, error: 'No active tab' });
  }

  try {
    const response = await chrome.tabs.sendMessage(activeTabId, {
      tool: tool,
      args: args
    });

    return JSON.stringify(response || { success: false, error: 'No response from content script' });
  } catch (error) {
    return JSON.stringify({ success: false, error: error.message });
  }
}

// Track active tab
chrome.tabs.onActivated.addListener((activeInfo) => {
  activeTabId = activeInfo.tabId;
  console.log('Active tab changed:', activeTabId);
});

// Handle connections from sidepanel
chrome.runtime.onConnect.addListener((port) => {
  if (port.name === 'sidepanel') {
    console.log('Sidepanel connected');
    sidepanelPort = port;

    // Send current connection status
    port.postMessage({
      type: 'ws_status',
      connected: ws && ws.readyState === WebSocket.OPEN
    });

    // Handle messages from sidepanel
    port.onMessage.addListener((msg) => {
      console.log('Message from sidepanel:', msg.type);
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(msg));
      }
    });

    port.onDisconnect.addListener(() => {
      console.log('Sidepanel disconnected');
      sidepanelPort = null;
    });
  }
});

// Set side panel behavior
chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch((error) => {
  console.error('Error setting panel behavior:', error);
});

console.log('BrowserAgent background script loaded');
