# BrowserAgent - Chrome Extension Loading Guide

## Step-by-Step Instructions

### 1. Open Chrome Extensions Page
- Open Google Chrome
- Type in address bar: `chrome://extensions/`
- Press Enter

### 2. Enable Developer Mode
- Look for "Developer mode" toggle in the top-right corner
- Click to enable it (should turn blue/on)

### 3. Load the Extension
- Click "Load unpacked" button (appears after enabling Developer mode)
- Navigate to: `D:\Orbi\extension`
- Click "Select Folder"

### 4. Pin the Extension
- Look for the puzzle piece icon in Chrome toolbar (extensions menu)
- Find "BrowserAgent" in the list
- Click the pin icon next to it
- The BrowserAgent icon should now appear in your toolbar

### 5. Configure and Test
- Click the BrowserAgent icon (should open a popup)
- Verify "Server URL" shows: `http://localhost:8001`
- Click "Test Connection"
- Should see: "✓ Connected (v3.0.0)"

### 6. Open Side Panel
- Click the BrowserAgent icon again
- The side panel should open on the right side
- You should see:
  - 3 agent pills: Sales Analyzer, Page Summarizer, Form Filler
  - A chat interface
  - An input box at the bottom

### 7. Test Your First Task
- Navigate to any webpage (try Wikipedia)
- In the side panel, click "Page Summarizer"
- Type: "Summarize this page"
- Press Send or Enter
- Watch the plan appear and execute!

## Troubleshooting

### Extension Won't Load
- Make sure you selected the `extension` folder, not the root `Orbi` folder
- Check for errors in the extensions page
- Try reloading the extension

### Connection Test Fails
- Verify server is running (check terminal)
- Make sure URL is `http://localhost:8001`
- Try restarting the server

### Side Panel Doesn't Open
- Right-click the extension icon → "Open side panel"
- Or check Chrome settings → Extensions → BrowserAgent → Details

### No Agents Showing
- Check browser console (F12) for errors
- Verify server URL in popup settings
- Reload the extension

## What You Should See

### Popup (Click Extension Icon)
```
BrowserAgent
Server URL: http://localhost:8001
[Test Connection] [Save Settings]
[Manage Agents]
Session ID: [uuid]
```

### Side Panel (Main Interface)
```
BrowserAgent [status dot] [Ask Mode toggle]
[Sales Analyzer] [Page Summarizer] [Form Filler]
---
Welcome to BrowserAgent
Select an agent above or let the orchestrator choose...
---
[Text input box]
[Send] [Clear]
```

## Next Steps After Loading

1. Test Page Summarizer on a Wikipedia article
2. Try Sales Analyzer on a page with numbers/data
3. Create your first custom agent via "Manage Agents"
4. Explore Ask Mode for step-by-step approval

---

Server Status: ✅ Running on http://localhost:8001
Extension Location: D:\Orbi\extension
Ready to load!
