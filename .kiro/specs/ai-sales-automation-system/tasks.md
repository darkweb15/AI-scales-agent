# Implementation Plan: AI Sales Automation System

## Overview

Implement the AI Sales Automation System in Python — a multi-agent platform with a central Orchestrator, six specialized agents, a distributed task queue, and a real-time SaaS dashboard. The implementation follows the design document's architecture: shared PostgreSQL prospect database, BullMQ-equivalent async task queue (Celery + Redis), and a Next.js/React frontend dashboard.

The backend is a Python service (FastAPI) exposing REST and WebSocket endpoints. Each agent is an independent Python module. The frontend is a Next.js (TypeScript/React) application using Tailwind CSS, shadcn/ui, and Recharts.

---

## Tasks

- [x] 1. Set up project structure, shared data models, and database layer
  - Create monorepo layout: `backend/` (FastAPI + agents), `frontend/` (Next.js)
  - Define all SQLAlchemy ORM models: `Lead`, `InteractionLog`, `AgentTask`, `EmailTemplate`, `Booking`
  - Implement `LeadStatus`, `AgentType`, `Channel`, `Intent` enums
  - Write Alembic migration for initial schema
  - Implement `DatabaseService` with CRUD helpers used by all agents
  - _Requirements: 8.1, 8.2, 8.5_

  - [ ]* 1.1 Write property test for LeadStatus monotonic progression
    - **Property 4: Lead Status Monotonic Progression**
    - **Validates: Requirements 8.1**
    - Use Hypothesis to generate arbitrary sequences of status transitions and assert no backward regression

- [x] 2. Implement core infrastructure: task queue, notification service, and config
  - Set up Celery + Redis as the task queue (`TaskQueue` wrapper)
  - Implement `NotificationService` with in-app event emission and Slack webhook delivery
  - Implement `Config` dataclass loading from environment variables (poll interval, cooldown, max attempts, thresholds, etc.)
  - Implement HMAC webhook signature verification middleware
  - _Requirements: 9.1, 9.2, 9.3, 8.6_

  - [ ]* 2.1 Write property test for HMAC webhook rejection
    - **Property 12: HMAC Webhook Rejection**
    - **Validates: Requirements 8.6**
    - Use Hypothesis to generate arbitrary payloads with invalid/missing signatures and assert all are rejected with 401

- [x] 3. Implement the Orchestrator
  - Implement `Orchestrator.run()` polling loop with configurable interval
  - Implement `Orchestrator.evaluate_lead(lead)` routing algorithm covering all LeadStatus branches
  - Implement `Orchestrator.dispatch(task)` to enqueue tasks via `TaskQueue`
  - Implement `Orchestrator.handle_outcome(outcome)` to persist results and update lead fields
  - Implement `is_on_cooldown(lead)` with NULL-safe logic
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10_

  - [ ]* 3.1 Write property test for DNC/unsubscribed leads never dispatched
    - **Property 1: DNC and Unsubscribed Leads Never Dispatched**
    - **Validates: Requirements 1.6, 8.3**
    - Use Hypothesis to generate leads with `do_not_contact` or `unsubscribed` status and assert `evaluate_lead` always returns None

  - [ ]* 3.2 Write property test for cooldown window correctness
    - **Property 2: Cooldown Window Correctness**
    - **Validates: Requirements 1.7, 1.8**
    - Use Hypothesis to generate arbitrary `last_contacted_at` timestamps and assert `is_on_cooldown` returns the correct boolean

  - [ ]* 3.3 Write property test for lead routing determinism
    - **Property 3: Lead Routing Determinism**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**
    - Use Hypothesis to generate lead states and assert `evaluate_lead` is pure and deterministic (same input → same output)

- [x] 4. Checkpoint — Ensure all Orchestrator tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement the Cold Calling Agent
  - Implement `ColdCallingAgent.call(lead)` with DNC check, calling-hours guard, and telephony API integration (Twilio/Bland AI stub)
  - Implement `handle_voicemail(lead)` to leave a scripted voicemail
  - Implement `transcribe_call(call_id)` returning a `Transcript` object
  - Integrate NLP intent extraction (`nlp_engine.extract_intent(transcript)`)
  - Persist call outcome and update lead status via `DatabaseService`
  - Implement exponential backoff retry on telephony API failure
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10_

  - [ ]* 5.1 Write unit tests for Cold Calling Agent
    - Test DNC block path (req 2.1), outside-hours deferral (req 2.2), no-answer increment (req 2.3), voicemail path (req 2.4), intent → status mapping (req 2.6, 2.7, 2.8)
    - Mock telephony API and NLP engine
    - _Requirements: 2.1–2.10_

- [x] 6. Implement the Auto Mail Sending Agent
  - Implement `AutoMailAgent.personalize_content(lead, template)` using LLM service to replace all template variables
  - Implement `AutoMailAgent.send_email(lead, template)` with email provider integration (SendGrid/SES stub)
  - Implement `AutoMailAgent.schedule_email(lead, template, send_at)` for deferred sends
  - Implement `AutoMailAgent.track_open(email_id)` and webhook handlers for open/click/unsubscribe events
  - Enforce unsubscribed suppression before every send
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_

  - [ ]* 6.1 Write property test for email personalization completeness
    - **Property 5: Email Personalization Completeness**
    - **Validates: Requirements 5.1, 5.2**
    - Use Hypothesis to generate arbitrary valid Lead records and EmailTemplate objects and assert output is non-empty with no unresolved placeholders

  - [ ]* 6.2 Write property test for unsubscribe suppression
    - **Property 10: Unsubscribe Suppression**
    - **Validates: Requirements 5.8, 8.3**
    - Use Hypothesis to generate leads with `unsubscribed` status and arbitrary templates and assert `send_email` never dispatches

- [x] 7. Implement the Follow-up Agent
  - Implement `FollowUpAgent.select_channel(lead)` with channel-alternation logic and null-phone guard
  - Implement `FollowUpAgent.execute_follow_up(lead)` with max-attempts escalation and multi-channel dispatch
  - Implement `FollowUpAgent.schedule_follow_up(lead, delay_hours)` to enqueue a deferred task
  - Personalize follow-up content via LLM service using prior interaction context
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [x]* 7.1 Write property test for channel selection safety
    - **Property 6: Channel Selection Safety**
    - **Validates: Requirements 3.2, 3.3, 3.4, 3.5**
    - Use Hypothesis to generate leads with null/non-null phone and arbitrary interaction histories and assert `select_channel` never returns `sms` for null-phone leads

  - [x]* 7.2 Write property test for follow-up escalation at max attempts
    - **Property 7: Follow-up Escalation at Max Attempts**
    - **Validates: Requirements 3.1**
    - Use Hypothesis to generate leads where `email_attempts + call_attempts >= config.maxTotalFollowUpAttempts` and assert escalation always fires

- [x] 8. Implement the Demo Scheduling Agent
  - Implement `DemoSchedulingAgent.propose_slots(lead)` fetching calendar availability and sending slot-proposal email
  - Implement `DemoSchedulingAgent.confirm_booking(lead, slot)` creating calendar event, saving `Booking`, and sending confirmation email
  - Implement `DemoSchedulingAgent.send_reminder(booking)` for 24h and 1h pre-demo reminders
  - Implement `DemoSchedulingAgent.handle_reschedule(booking, new_slot)` updating booking and re-proposing slots
  - Handle calendar conflict (slot unavailable between proposal and confirmation)
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9_

  - [x]* 8.1 Write unit tests for Demo Scheduling Agent
    - Test no-slots-available admin notification (req 4.3), slot conflict re-proposal (req 4.5), 24h and 1h reminder triggers (req 4.6, 4.7), reschedule flow (req 4.8)
    - Mock Calendar API and Auto Mail Agent
    - _Requirements: 4.1–4.9_

- [x] 9. Implement the Auto Reply Agent
  - Implement `AutoReplyAgent.receive_message(message)` with lead lookup / creation from inbound email
  - Implement `AutoReplyAgent.classify_intent(message)` returning one of the defined `Intent` values
  - Implement `AutoReplyAgent.generate_reply(lead, intent)` using LLM service with prompt injection guardrails
  - Implement confidence-threshold escalation path (no reply sent when below threshold)
  - Handle unsubscribe intent: update status + send confirmation template without LLM
  - Notify Orchestrator on reply sent
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8_

  - [ ]* 9.1 Write property test for intent classification coverage
    - **Property 8: Auto Reply Intent Classification Coverage**
    - **Validates: Requirements 6.6**
    - Use Hypothesis to generate arbitrary inbound message strings and assert `classify_intent` always returns a valid, non-null `Intent` value

  - [ ]* 9.2 Write property test for low-confidence escalation
    - **Property 9: Low-Confidence Escalation**
    - **Validates: Requirements 6.4**
    - Use Hypothesis to generate messages with confidence scores below threshold and assert no automated reply is sent and escalation always fires

- [x] 10. Implement the Call Answering Agent
  - Implement `CallAnsweringAgent.answer_call(call_id, caller)` with lead lookup / creation from inbound call
  - Implement `CallAnsweringAgent.qualify_caller(call_id)` running AI qualification conversation
  - Implement `CallAnsweringAgent.route_to_human(call_id, reason)` for explicit requests and low-confidence transfers
  - Implement `CallAnsweringAgent.log_call(call_id, summary)` persisting transcript and qualification outcome
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [ ]* 10.1 Write unit tests for Call Answering Agent
    - Test human-transfer on explicit request (req 7.2), low-confidence transfer (req 7.3), new lead creation from inbound (req 7.6), interaction log persistence (req 7.4)
    - Mock telephony API and LLM service
    - _Requirements: 7.1–7.6_

- [x] 11. Implement lead lifecycle guards and audit log enforcement
  - Add pre-dispatch guard in `Orchestrator.dispatch()` verifying lead is not `do_not_contact` or `unsubscribed`
  - Enforce append-only `InteractionLog` at the ORM level (no update/delete methods exposed)
  - Implement `requires_human_review` escalation path when `AgentTask` exceeds `config.maxTaskRetries`
  - Encrypt PII fields (`phone`, `email`, `first_name`, `last_name`) at rest using SQLAlchemy column-level encryption
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* 11.1 Write property test for audit log append-only invariant
    - **Property 11: Audit Log Append-Only Invariant**
    - **Validates: Requirements 8.2**
    - Use Hypothesis to generate sequences of agent actions and assert no `InteractionLog` entry is ever mutated or deleted after creation

- [x] 12. Checkpoint — Ensure all agent and infrastructure tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Implement FastAPI backend: REST API and WebSocket server
  - Implement REST endpoints for leads (CRUD, bulk actions, status update, CSV export)
  - Implement REST endpoints for agent control (pause, resume, cancel task, update config)
  - Implement REST endpoints for bookings (confirm, reschedule, cancel, send reminder)
  - Implement REST endpoints for analytics (KPIs, funnel, agent performance, email metrics, call outcomes, lead source)
  - Implement REST endpoints for notifications (list, mark read, settings)
  - Implement WebSocket server pushing events: `agent.status_changed`, `task.completed`, `task.failed`, `lead.status_changed`, `notification.new`, `kpi.updated`
  - _Requirements: 9.1, 10.1–10.7, 11.1–11.8, 12.1–12.7, 16.1–16.7, 17.1–17.7_

- [x] 14. Implement dashboard foundation: Next.js app shell, design system, and routing
  - Bootstrap Next.js app with Tailwind CSS v4, shadcn/ui, and Inter + JetBrains Mono fonts
  - Implement global CSS variables for the dark-theme color palette (`--bg-base`, `--accent-blue`, etc.)
  - Implement the global shell: collapsible sidebar (220px / 56px), topbar with search, notification bell, and user avatar
  - Implement responsive breakpoints (mobile drawer, tablet icon-only, desktop pinned)
  - Implement light/dark theme toggle with `localStorage` persistence
  - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6_

- [x] 15. Implement Dashboard home screen (`/dashboard`)
  - Implement four KPI metric cards with sparklines (Recharts `AreaChart`), trend indicators, and animated number transitions (600ms)
  - Implement six agent status cards with pulsing status dots, queue depth, completions, last action, and Pause/Resume buttons
  - Implement horizontal pipeline funnel bar with proportional segments and hover tooltips
  - Implement real-time activity feed (last 50 events, newest first, color-coded by agent)
  - Wire all components to REST API and WebSocket events (`agent.status_changed`, `task.completed`, `kpi.updated`)
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

  - [ ]* 15.1 Write property test for pipeline funnel accuracy
    - **Property 13: Pipeline Funnel Accuracy**
    - **Validates: Requirements 10.5**
    - Use Hypothesis to generate arbitrary lead databases and assert funnel counts exactly match per-status lead counts

- [x] 16. Implement Lead Management view (`/leads`)
  - Implement sortable, filterable TanStack Table v8 with all required columns and virtualization
  - Implement full-text search with 300ms debounce and matched-text highlighting
  - Implement multi-select filters (status, source, agent, date range) synced to URL query params
  - Implement kanban view with drag-and-drop status updates (optimistic UI + rollback on API failure)
  - Implement bulk action controls (reassign, change status, export CSV, mark DNC, delete with confirmation)
  - Implement lead row click → Interaction Timeline slide-over
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8_

  - [ ]* 16.1 Write property test for filter result correctness
    - **Property 14: Filter Result Correctness**
    - **Validates: Requirements 11.2**
    - Use Hypothesis to generate arbitrary lead sets and filter combinations and assert every displayed lead satisfies all active filters

  - [ ]* 16.2 Write property test for bulk action completeness
    - **Property 15: Bulk Action Completeness**
    - **Validates: Requirements 11.7**
    - Use Hypothesis to generate arbitrary lead selections and bulk actions and assert the action is applied to every selected lead

- [x] 17. Implement Agent Control Panel (`/agents`)
  - Implement agent selector tabs (one per agent)
  - Implement agent header with animated status dot, Pause/Resume toggle (with loading spinner), and "View Config" slide-over
  - Implement stats row (queue depth, running, completed today, failed today)
  - Implement live task queue list (priority-sorted, cancel button with confirmation)
  - Implement recent completions panel (last 20 tasks with outcome badges)
  - Implement editable agent config slide-over (max attempts, cooldown, calling hours, confidence thresholds)
  - Wire to REST API and WebSocket `agent.status_changed` / `task.completed` / `task.failed` events
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7_

- [ ] 18. Implement Interaction Timeline (`/leads/:id` and slide-over)
  - Implement lead header with editable status dropdown and tags chip input
  - Implement lead details panel with editable notes (auto-save on blur) and read-only metadata
  - Implement chronological interaction timeline with call, email, and demo event cards
  - Implement call card with AI summary, outcome badge, play-recording button, and expandable transcript viewer (JetBrains Mono, speaker-labeled turns, intent highlighting)
  - Implement email card with subject, open/click status badges, and preview expand
  - Implement demo card with date, status, and meeting link
  - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_

- [x] 19. Implement Demo Scheduling view (`/demos`)
  - Implement react-big-calendar week view with demo events color-coded by booking status
  - Implement booking detail slide-over (lead info, date/time, status, meeting link, action buttons)
  - Implement "Send Reminder" action (triggers API call + confirmation toast)
  - Implement "Reschedule" slot picker (fetches live calendar availability)
  - Implement "Cancel" with confirmation dialog and optional cancellation message
  - Implement upcoming demos list grouped by day (right panel)
  - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6_

- [x] 20. Implement Analytics & Reporting view (`/analytics`)
  - Implement full-width conversion funnel chart (Recharts `FunnelChart`) with click-to-filter integration
  - Implement agent performance bar chart + summary table (tasks, success rate, avg response time, escalations)
  - Implement email metrics line chart (open rate, click rate, reply rate) + summary cards
  - Implement call outcomes donut chart (Recharts `PieChart`) with center label
  - Implement lead source breakdown horizontal bar chart with conversion rate overlay
  - Implement date range picker that updates all charts and cards
  - Implement "Export CSV" and "Export PDF" download actions
  - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7, 15.8_

- [ ] 21. Implement Notification Center (slide-over panel)
  - Implement notification slide-over triggered from topbar bell icon with unread count badge
  - Implement tabbed view: All, Escalations, System, Reminders
  - Implement escalation queue tab with lead name, reason, agent, time, and Review/Dismiss/Reassign actions
  - Implement "Review" action opening Interaction Timeline in a modal
  - Implement per-type notification settings (in-app, email digest, Slack webhook)
  - Wire to WebSocket `notification.new` event for real-time badge increment and panel prepend
  - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 16.7_

  - [ ]* 21.1 Write property test for notification categorization
    - **Property 17: Notification Categorization**
    - **Validates: Requirements 16.3**
    - Use Hypothesis to generate arbitrary notification payloads and assert each is assigned exactly one valid type and appears only in the correct tab

- [x] 22. Implement WebSocket client and real-time update handling
  - Implement WebSocket client hook (`useWebSocket`) with exponential backoff reconnect (1s → 2s → 4s → max 30s)
  - Implement "Reconnecting..." banner shown on disconnect, auto-dismissed on restore
  - Implement full data refresh on reconnect to reconcile missed events
  - Wire `agent.status_changed` → agent card update, `task.completed` → counter + activity feed, `lead.status_changed` → table row update, `kpi.updated` → animated KPI card transition
  - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7_

  - [ ]* 22.1 Write property test for WebSocket reconnect backoff
    - **Property 16: WebSocket Reconnect Backoff**
    - **Validates: Requirements 17.6**
    - Use Hypothesis to generate sequences of disconnection events and assert delay intervals follow exponential backoff capped at 30s

- [ ] 23. Implement global command palette, keyboard navigation, and accessibility
  - Implement `⌘K` / `Ctrl+K` global command palette (shadcn/ui Command) searching leads, agents, interactions, and docs
  - Implement `Escape` to close any open modal, slide-over, or dropdown
  - Implement `J` / `K` keyboard navigation in leads table and task queue
  - Add `aria-label` attributes to all status badges and icon-only buttons
  - Implement visible focus rings (`2px solid --accent-blue`, `2px offset`) in both themes
  - Ensure all interactive elements are reachable via `Tab` in logical order
  - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5_

- [ ] 24. Implement skeleton loaders, empty states, and error states
  - Implement page-level skeleton layouts (shimmer animation) for all routes
  - Implement component-level skeletons for cards, tables, and charts
  - Implement empty states with icon, headline, description, and CTA for all views
  - Implement inline field errors, component error cards with retry, and page-level error boundaries
  - Implement toast notification system (slide-in from bottom-right, 4s auto-dismiss, stack up to 3)
  - _Requirements: 18.7 (skeleton loaders), 10.4 (error state on agent card)_

- [ ] 25. Wire everything together and final integration
  - Connect all frontend views to their respective backend REST endpoints
  - Ensure all WebSocket event types are emitted by the backend on every relevant state change
  - Verify all agent actions check DNC/unsubscribed status before dispatch (pre-dispatch guard)
  - Verify LLM prompts include system-level prompt injection guardrails in all agents
  - Run the full test suite and fix any remaining failures
  - _Requirements: 8.3, 8.7, 9.4, 9.5_

- [ ] 26. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- All property tests use [Hypothesis](https://hypothesis.readthedocs.io/) (Python PBT library)
- Each property test task references the specific property number from the design document
- Backend: FastAPI + SQLAlchemy + Celery + Redis + PostgreSQL
- Frontend: Next.js (TypeScript) + Tailwind CSS v4 + shadcn/ui + Recharts + TanStack Table + react-big-calendar + Framer Motion
- External integrations (Twilio, SendGrid, Google Calendar, OpenAI) should be implemented behind interface abstractions to allow easy swapping
- Checkpoints ensure incremental validation at key milestones
