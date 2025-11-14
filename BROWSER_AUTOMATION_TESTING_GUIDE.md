# Browser Automation Testing Guide

## Overview
The browser automation feature allows the AI agent to actually log into Sleeper and make lineup changes for you. It opens a headless browser, navigates to your lineup, and executes the changes while taking screenshots.

---

## Step-by-Step Testing Instructions

### 1. Save Your Sleeper Credentials

First, you need to save your Sleeper login credentials so the agent can log in on your behalf.

**Option A: Via Frontend UI**
1. Navigate to: http://localhost:3000/settings
2. Scroll to "Sleeper Login Credentials" section
3. Enter your email and password
4. Uncheck "Use Google SSO" (unless you use Google SSO)
5. Click "Save Credentials"
6. Click "Test Connection" to verify they work

**Option B: Via API**
```bash
curl -X POST http://localhost:8000/api/v1/browser/credentials \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "default",
    "email": "your-sleeper-email@example.com",
    "password": "your-sleeper-password",
    "use_sso": false
  }'
```

### 2. Open the Agent Window

Navigate to the agent page:
```
http://localhost:3000/agent?league_id=YOUR_LEAGUE_ID&roster_id=YOUR_ROSTER_ID&week=9
```

Replace:
- `YOUR_LEAGUE_ID` with your actual Sleeper league ID
- `YOUR_ROSTER_ID` with your roster ID (usually 1-12)
- `week` with the current week number

**To find your league/roster IDs:**
1. Go to Sleeper and open your league
2. Look at the URL - it will be like: `https://sleeper.app/leagues/1234567890/team`
3. The long number is your league ID
4. Your roster ID is usually 1-12 (try different numbers to find yours)

### 3. Test Browser Automation Commands

Once the agent window is open, try these commands:

#### Test 1: Simple Browser Navigation
```
"Open Sleeper and show me the homepage"
```
**Expected Result:**
- Agent opens browser
- Navigates to sleeper.app
- Takes a screenshot
- Shows screenshot in the UI

#### Test 2: Login Test
```
"Log into my Sleeper account"
```
**Expected Result:**
- Agent retrieves your saved credentials
- Logs into Sleeper
- Takes a screenshot of logged-in page
- Confirms successful login

#### Test 3: Navigate to Lineup
```
"Go to my Week 9 lineup for league [YOUR_LEAGUE_ID]"
```
**Expected Result:**
- Agent navigates to specific lineup page
- Takes screenshot
- Shows current lineup state

#### Test 4: Full Lineup Change (THE BIG TEST)
```
"Set my optimal lineup for Week 9"
```
**Expected Result:**
1. Agent analyzes your roster
2. Shows recommended changes
3. **Asks for confirmation**
4. Once confirmed:
   - Opens browser
   - Logs into Sleeper
   - Navigates to your lineup
   - Takes "before" screenshot
   - Makes each swap
   - Takes screenshots during swaps
   - Saves lineup
   - Takes "after" screenshot
   - Shows all screenshots in UI

---

## What You Should See in the UI

### Control Panel (Top)
- **Status Badge**: Shows "Running" when agent is working
- **Session ID**: Your browser session identifier
- **Run/Stop/Pause**: Control buttons (mostly automatic)
- **Autopilot Toggle**: When ON, agent executes without asking

### Left Panel (40% width)
- **Chat Messages**: Conversation with agent
- **Tool Execution Cards**: Shows each tool being called
  - `open_page` - Opening URLs
  - `sleeper_login` - Logging in
  - `navigate_to_lineup` - Going to lineup
  - `click_element` - Clicking buttons
  - `take_screenshot` - Capturing screenshots

### Right Panel (60% width)
- **Top: Progress Timeline**
  - Shows step-by-step progress
  - Each step shows status (pending/active/completed/error)

- **Bottom: Screenshot Gallery**
  - Horizontal scrollable strip
  - Click any screenshot to enlarge
  - Shows all captured screenshots with tags

---

## Example Full Test Scenario

Let's do a complete test of the lineup change feature:

### Step 1: Start Fresh
```
"Hi! I want to optimize my lineup for Week 9"
```

### Step 2: Agent Analyzes
The agent will:
- Fetch your current roster
- Get player projections for Week 9
- Analyze optimal lineup
- Show you recommended changes like:
  ```
  Recommended Changes:
  1. Start: Christian McCaffrey (RB) - 18.5 projected pts
     Bench: Zach Charbonnet (RB) - 8.2 projected pts

  2. Start: CeeDee Lamb (WR) - 15.3 projected pts
     Bench: Tyler Lockett (WR) - 9.1 projected pts
  ```

### Step 3: Confirm Changes
You respond:
```
"Yes, make those changes"
```

### Step 4: Watch the Magic
The agent will:

1. **Initialize Browser**
   - You'll see: "Starting browser session..."
   - Status: Tool card for `open_page`

2. **Login**
   - You'll see: "Logging into Sleeper..."
   - Screenshot 1: Login page

3. **Navigate to Lineup**
   - You'll see: "Navigating to your lineup..."
   - Screenshot 2: Before changes

4. **Make Swaps**
   - For each swap:
     - Tool card: `click_element`
     - Screenshot: During swap

5. **Save Changes**
   - Tool card: `click_element` (save button)
   - Screenshot 3: After changes

6. **Summary**
   - Agent shows all screenshots
   - Confirms changes were made
   - Closes browser session

---

## Troubleshooting

### "Failed to start browser session"
- Check Docker logs: `docker logs fantasy-backend --tail 50`
- Ensure Playwright is installed correctly
- Try rebuilding: `docker-compose build backend`

### "Credentials not found"
- Save credentials first (Step 1)
- Verify with: `curl http://localhost:8000/api/v1/browser/credentials/default`

### "Can't find element"
- Sleeper UI may have changed
- Check selectors in `backend/app/tools/browser/selectors.py`
- Try updating selectors

### Agent doesn't ask for confirmation
- Check if "Autopilot" is enabled (should be OFF for first tests)
- Agent should always ask before making changes

### Screenshots not showing
- Check browser logs: `docker logs fantasy-backend | grep screenshot`
- Verify screenshots directory: `ls -la backend/data/screenshots/`
- Check static file serving: `curl http://localhost:8000/uploads/`

---

## Advanced Testing

### Test Individual Browser Tools

You can test browser tools directly via API:

**1. Start a Session**
```bash
curl -X POST http://localhost:8000/api/v1/browser/start-session \
  -H 'Content-Type: application/json' \
  -d '{"user_id": "default"}'
```
Save the `session_id` from response.

**2. Open Page**
```bash
curl -X POST http://localhost:8000/api/v1/browser/execute \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "YOUR_SESSION_ID",
    "tool": "open_page",
    "args": {"url": "https://sleeper.app"}
  }'
```

**3. Take Screenshot**
```bash
curl -X POST http://localhost:8000/api/v1/browser/execute \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "YOUR_SESSION_ID",
    "tool": "take_screenshot",
    "args": {"tag": "test"}
  }'
```

---

## Safety Features

The browser automation has several safety features:

1. **Domain Whitelist**: Only allowed to access:
   - sleeper.app
   - sleeper.com
   - accounts.google.com (for SSO)

2. **User Confirmation**: Always asks before making lineup changes

3. **Screenshot Logging**: Takes screenshots at every step for verification

4. **Persistent Sessions**: Maintains login between requests (stays logged in)

5. **Timeout Protection**: All operations have 30-second timeouts

6. **Error Recovery**: Gracefully handles failures and reports errors

---

## What to Report Back

When testing, please note:

1. **Success Indicators:**
   - ✅ Browser session starts
   - ✅ Screenshots appear in UI
   - ✅ Tool cards show success status
   - ✅ Timeline shows progress
   - ✅ Lineup changes actually happen on Sleeper

2. **Issues to Report:**
   - ❌ Error messages in chat
   - ❌ Tool cards showing "error" status
   - ❌ Screenshots not appearing
   - ❌ Changes not saved to Sleeper
   - ❌ Browser automation doesn't start

3. **Performance:**
   - How long did the full flow take?
   - Were there any delays or timeouts?
   - Did screenshots load quickly?

---

## Quick Test Script

Here's a quick test you can run:

```bash
# 1. Save credentials
curl -X POST http://localhost:8000/api/v1/browser/credentials \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"default","email":"YOUR_EMAIL","password":"YOUR_PASS","use_sso":false}'

# 2. Start browser session
curl -X POST http://localhost:8000/api/v1/browser/start-session \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"default"}'

# 3. Check it worked
curl http://localhost:8000/api/v1/browser/sessions

# 4. Now open the UI and test chat
# http://localhost:3000/agent?league_id=YOUR_LEAGUE&roster_id=1&week=9
```

---

## Expected Timeline for Full Lineup Change

| Step | Time | What Happens |
|------|------|--------------|
| 1. Analyze roster | 2-3s | Fetch data, calculate optimal lineup |
| 2. Show recommendations | 1s | Display proposed changes |
| 3. User confirms | 0s | Wait for user |
| 4. Start browser | 3-5s | Launch Chromium, create session |
| 5. Login to Sleeper | 5-8s | Navigate, enter credentials, wait for redirect |
| 6. Navigate to lineup | 3-5s | Go to specific league/week |
| 7. Make swaps | 10-20s | Click elements, drag/drop, wait for UI |
| 8. Save changes | 2-3s | Click save, wait for confirmation |
| 9. Take screenshots | 1-2s per screenshot | Capture and save images |
| 10. Close session | 1s | Clean up |

**Total: ~30-50 seconds** for a full lineup optimization with 2-3 swaps.

---

## Next Steps After Testing

Once you've tested and it works:

1. **Enable Autopilot**: Turn on autopilot mode for automatic execution
2. **Schedule Jobs**: Set up automated lineup optimization
3. **Add More Tools**: We can add more browser automation tools as needed
4. **Customize Prompts**: Adjust agent behavior for your preferences

---

Good luck testing! Let me know what you see when you try the commands above.
