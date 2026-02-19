# BrowserAgent v3.0

**Open-Source Chrome Extension | Sub-Agent Orchestration | Universal Plan-then-Execute**

BrowserAgent is an open-source Chrome extension that gives anyone with an OpenRouter API key a Claude-in-Chrome equivalent — plus a unique Sub-Agent system and a Universal Plan-then-Execute architecture.

## 🎯 Key Features

- **Plan-then-Execute Architecture**: Every request generates a visible execution plan before any action is taken
- **Sub-Agent System**: Create specialized agents for different tasks (Sales Analyzer, Form Filler, etc.)
- **Real-Time Todo Tracking**: Watch your plan get checked off step-by-step in the side panel
- **Autonomous Operation**: Agents work independently, only asking permission for destructive actions
- **Automatic Recovery**: Failed steps trigger automatic replanning
- **Complete Audit Trail**: Every action is logged and mapped to a todo step

## 📋 Prerequisites

- **Python 3.11+**
- **Chrome Browser**
- **OpenRouter API Key** ([Get one here](https://openrouter.ai/))

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenRouter API key:

```
OPENROUTER_API_KEY=your_key_here
```

### 3. Start the Server

```bash
python run.py
```

The server will start on `http://localhost:8001`

### 4. Load Chrome Extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top-right)
3. Click "Load unpacked"
4. Select the `extension` folder from this project
5. Click the BrowserAgent icon in your toolbar to open the side panel

### 5. Test the Connection

1. Click the BrowserAgent extension icon
2. In the popup, verify the server URL is `http://localhost:8001`
3. Click "Test Connection"
4. You should see "✓ Connected"

## 🎓 How It Works

### The Plan-then-Execute Flow

BrowserAgent's defining feature is that **planning is non-negotiable and universal**. Here's what happens when you send a request:

1. **User sends message**: "Analyze the sales data on this page"
2. **Planner generates todos**: A fast LLM call creates an ordered list of atomic steps
3. **Plan displayed**: You see the full execution plan in the side panel
4. **Approval** (optional): In Ask mode, you can review and edit before execution
5. **Execution**: The agent works through each step, calling `mark_todo_done()` after each
6. **Real-time updates**: Watch checkmarks appear as steps complete
7. **Auto-recovery**: If a step fails, the system automatically generates replacement steps

### Example Plan

```
1. [pending] Read the current page to find sales data
2. [pending] Extract revenue figures from the table
3. [pending] Identify top 3 products by revenue
4. [pending] Format and present the analysis
```

As the agent works, you'll see each step turn green with a checkmark.

## 🤖 Creating Sub-Agents

Sub-agents are specialized workers for specific tasks. To create one:

1. Click the extension icon → "Manage Agents"
2. Click "+ New Agent"
3. Fill in the form:

### Agent Description (Most Important!)

The description field answers: **"When should the Orchestrator pick me?"**

**Good Examples:**
- "Use me when you need to analyze sales data, revenue figures, KPIs, or conversion rates visible on the current page"
- "Use me when the user needs to fill in a web form, enter data into fields, or complete a multi-field input process"

**Bad Examples:**
- "I analyze sales data" (doesn't explain WHEN)
- "I fill forms" (too vague)

### System Prompt

Detailed instructions for the agent's behavior. The planning execution rules are automatically appended.

### Tools

Select only the tools this agent needs. Less is more — minimal permissions = better security.

**Tool Categories:**
- **Page Reading**: read_page, get_page_text, screenshot, scroll_page
- **Interaction**: click_element, type_text, select_option, check_element
- **Navigation**: navigate_to, go_back
- **Tab Management**: get_tabs_context, open_new_tab, close_tab
- **Advanced** (use with caution): javascript_tool, read_network

## 🔒 Permission Modes

### Ask Mode (Toggle in side panel)
- Plan shown, approval required before execution
- Every tool call also asks for confirmation
- Best for sensitive sessions

### Auto Mode (Default)
- Plan shown, auto-approved after 2 seconds
- Fully autonomous execution
- DELETE-class actions still always confirm
- Best for most agents

## 🛡️ Security

### What Agents Do WITHOUT Asking

- Click: Save, Update, Submit, Apply, Publish, Send, Post, Next, Continue
- Type text into any input field
- Select dropdown options, check/uncheck boxes
- Navigate within the same website
- Scroll, read content, take screenshots

### What Agents ALWAYS Ask Before Doing

- Click buttons labeled: delete, remove, unsubscribe, deactivate, cancel account
- Upload files
- Execute JavaScript
- Navigate to a different website domain

### Security Architecture

- API keys stored only in server `.env` (never in extension)
- All page content treated as untrusted
- Input validation on all tool calls
- Server runs locally only (not exposed to internet)
- Planning-first architecture resists prompt injection

## 📊 Default Agents

BrowserAgent comes with 3 pre-configured agents:

1. **Sales Analyzer**: Extracts and analyzes revenue, KPIs, and metrics
2. **Page Summarizer**: Condenses articles and docs into bullet points
3. **Form Filler**: Identifies and fills web forms step-by-step

## 🔧 Troubleshooting

### "Server offline" error
- Make sure `python server.py` is running
- Check that the server URL in settings is `http://localhost:8000`
- Test the connection in the popup

### Extension not loading
- Make sure you loaded the `extension` folder (not the whole project)
- Check Chrome DevTools console for errors
- Try reloading the extension

### Agent not responding
- Check the browser console (F12) for errors
- Verify your OpenRouter API key is valid
- Check that the content script loaded (should see "BrowserAgent content script loaded" in console)

### WebSocket connection issues
- Restart the Python server
- Reload the Chrome extension
- Check firewall settings (localhost should be allowed)

## 📁 Project Structure

```
BrowserAgent/
├── extension/           # Chrome extension files
│   ├── manifest.json
│   ├── background.js   # WebSocket client, tool relay
│   ├── content.js      # Page interaction, accessibility tree
│   ├── sidepanel.html/js/css  # Main UI
│   ├── popup.html/js   # Settings
│   └── agents.html/js  # Agent manager
├── server/             # Python FastAPI server
│   ├── main.py         # FastAPI app, lifespan, CORS
│   ├── config.py       # Settings, env validation
│   ├── agents/         # AI orchestration
│   │   ├── planner.py  # Plan generation
│   │   ├── orchestrator.py  # Plan-then-execute pipeline
│   │   ├── factory.py  # Agent builder
│   │   ├── tools.py    # All 22 tool definitions
│   │   └── bridge.py   # WebSocket bridge
│   ├── db/             # SQLite persistence
│   │   ├── models.py   # Schema (6 tables)
│   │   ├── agent_service.py
│   │   ├── session_service.py
│   │   └── todo_service.py
│   └── routers/        # API endpoints
│       ├── ws.py       # WebSocket handler
│       ├── agents.py   # Agent CRUD
│       └── sessions.py # Session management
├── requirements.txt
├── server.py           # Entry point
├── .env.example
└── README.md
```

## 🎯 Use Cases

- **Sales Analysis**: Extract revenue data, KPIs, conversion rates from dashboards
- **LinkedIn Optimization**: Update profile, add skills, optimize headline
- **Form Automation**: Fill out job applications, surveys, contact forms
- **Research**: Summarize articles, extract key points, gather data
- **Testing**: Automated UI testing with natural language instructions

## 🤝 Contributing

BrowserAgent is open source (MIT License). Contributions welcome!

## 📝 License

MIT License - see LICENSE file for details

## 🔗 Links

- [OpenRouter](https://openrouter.ai/) - Get your API key
- [Documentation](PROJECT_CONSTITUTION.md) - Full technical specification

---

**BrowserAgent v3.0 — Plan. Execute. Check off.**

*Every agent. Every request. Always planned first.*
