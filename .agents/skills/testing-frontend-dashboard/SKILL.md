---
name: testing-frontend-dashboard
description: Test the AI Sales Agent frontend dashboard end-to-end. Use when verifying dark-mode UI, page rendering, or component changes.
---

# Testing the Frontend Dashboard

## Prerequisites
- Node.js installed
- Frontend dependencies installed: `cd frontend && npm install --legacy-peer-deps`

## Starting the Dev Server
```bash
cd frontend && npm run dev
```
Server runs on `http://localhost:3000`.

## Chrome Launch
The environment uses a wrapper script at `~/.local/bin/google-chrome` that opens tabs via CDP on port 29229. If Chrome isn't running, launch the real binary:
```bash
/opt/.devin/chrome/chrome/linux-133.0.6943.126/chrome-linux64/chrome \
  --remote-debugging-port=29229 \
  --user-data-dir=/home/ubuntu/.browser_data_dir \
  --no-first-run --disable-session-crashed-bubble \
  --no-default-browser-check http://localhost:3000 &disown
```
Then use `wmctrl -r "Google Chrome" -b add,maximized_vert,maximized_horz` to maximize.

## Pages to Test
1. **Dashboard** (`/`) — KPI cards, agent performance table, activity chart, AI insights, recent activities, AI assistant bar
2. **Leads** (`/leads`) — Search input, status filter, voice selector, lead table, status badges
3. **AddLeadModal** — Click "+ Add Lead" on Leads page. Verify dark modal overlay, dark form inputs, blue submit button
4. **Business Data** (`/business`) — Tab switcher (Analytics/Browse), import button, data quality metrics, charts
5. **Agents** (`/agents`) — Agent tabs (Cold Calling, Follow-up, etc.), status cards, live task queue, configuration panel
6. **Demos** (`/demos`) — Demo scheduling cards, status indicators
7. **Analytics** (`/analytics`) — KPI cards, pipeline funnel, lead sources chart, leads by status bar chart
8. **Campaigns** (`/campaigns`) — Campaign sequence steps, email controls, send button
9. **Sidebar** — Visible on all pages. Verify dark background, active item highlight, all nav links work

## Dark Theme Pass/Fail Criteria
- **PASS**: All backgrounds are dark (#0A0A0F base, #111118 surface, #1A1A24 elevated). Text is light (white/off-white). Accent colors visible (blue #4F8EF7, green #34D399, etc.). No white or light-gray areas.
- **FAIL**: Any white/light background, dark text on dark background (unreadable), browser-default styled elements with white backgrounds.

## Known Caveats
- Native `<select>` dropdown menus may show browser-default light backgrounds when opened — this is a CSS limitation and not a bug in the dark theme implementation.
- Backend must be running for data-dependent features (lead creation, API calls, agent actions). Without backend, UI renders with static/mock data which is sufficient for visual QA.
- ESLint has a pre-existing config issue (Next.js 14 vs eslint-config-next version mismatch). Use `npx next build` for type checking instead of `npm run lint`.

## Build Verification
```bash
cd frontend && npx next build
```
Should compile all 10 routes with 0 type errors.
