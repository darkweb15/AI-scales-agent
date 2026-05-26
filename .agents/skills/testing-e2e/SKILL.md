---
name: testing-e2e-ai-scales-agent
description: End-to-end testing of the AI-scales-agent application. Use when verifying UI functionality, API endpoints, LLM integration, or full agentic workflow changes.
---

# Testing AI-scales-agent End-to-End

## Devin Secrets Needed
- `GROQ_API_KEY` — Primary LLM provider (Groq, llama-3.3-70b)
- `OPENAI_API_KEY` — Fallback LLM provider (GPT-4o-mini, may have quota issues)

## Environment Setup

### Backend (FastAPI on port 8001)
```bash
cd /home/ubuntu/repos/AI-scales-agent/backend
# Ensure .env has DATABASE_URL, GROQ_API_KEY, OPENAI_API_KEY
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### Frontend (Next.js on port 3000)
```bash
cd /home/ubuntu/repos/AI-scales-agent/frontend
npm run dev
```

### Verify both are running
```bash
curl -s http://localhost:8001/api/leads?limit=1 | python3 -c "import sys,json; json.load(sys.stdin); print('Backend OK')"
curl -s -o /dev/null -w 'Frontend: HTTP %{http_code}' http://localhost:3000
```

## Key Test Scenarios

### 1. All 7 Pages Load
Navigate via sidebar: Dashboard, Leads, Business Data, Agents, Demos, Analytics, Campaigns.
Each page should render content with live Supabase data (not empty/placeholder).

### 2. Add Lead Modal
- Open from Topbar "Add Lead" button (works on all pages)
- Submit with only First Name + Email (last_name is optional)
- Verify validation error when required fields are empty
- Modal should close on success, not hang

### 3. AI Assistant Bar
- Click the input at bottom of Dashboard
- Suggestion pills should appear on focus
- Type a question and press Enter
- Wait up to 10s for LLM response (Groq API)
- If rate limited, wait 60s and retry

### 4. Leads Page Filters
- Search box filters by name/email/company
- Status dropdown filters by lead status (11 options)
- Voice provider dropdown shows 4 options

### 5. Agents Page
- All 6 agents should show "active" status
- Orchestrator should show "Running"
- Configuration panel should be editable

### 6. Sidebar Collapse/Expand
- Click "Collapse" at bottom of sidebar
- Should collapse to icon-only rail
- Click again to expand

## Known Issues & Workarounds

### Groq Rate Limiting
The orchestrator background task makes many LLM calls on startup, which may exhaust Groq's free-tier rate limit (30 req/min). If you see 429 errors:
- Wait 60 seconds for rate limit to reset
- Test AI endpoints individually after the rate limit resets
- This is a free-tier limitation, not a code bug

### OpenAI Fallback
OpenAI may return 429 errors due to quota limits. Groq is the primary provider.

### Backend Async Blocking
If API endpoints become unresponsive while the orchestrator is running, check that all LLM calls in `graph_orchestrator.py` and `ai_chat.py` use `asyncio.to_thread()`. Synchronous LLM calls (with `time.sleep()` and `requests.post()`) will block the event loop.

### Chrome for Testing
The VM's `google-chrome` wrapper requires CDP on port 29229. To launch Chrome directly:
```bash
DISPLAY=:0 /opt/.devin/chrome/chrome/linux-133.0.6943.126/chrome-linux64/chrome \
  --no-first-run --no-sandbox \
  --user-data-dir=/home/ubuntu/.chrome_test_profile \
  http://localhost:3000
```
Then maximize: `wmctrl -r "Google Chrome" -b add,maximized_vert,maximized_horz`

## Database
- Supabase PostgreSQL with 211+ leads, 83K+ business records
- Connection string in .env as DATABASE_URL
- Uses asyncpg for async database access
