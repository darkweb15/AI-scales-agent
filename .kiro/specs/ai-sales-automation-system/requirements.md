# Requirements Document

## Introduction

The AI Sales Automation System is a multi-agent platform that automates the full outbound and inbound sales lifecycle. Six specialized agents — Cold Calling, Follow-up, Demo Scheduling, Auto Mail Sending, Auto Reply, and Call Answering — operate autonomously under a central Orchestrator. All agents share a prospect database, coordinate through a task queue, and update lead state in real time. A premium dark-mode SaaS dashboard surfaces pipeline health, agent activity, and conversion metrics for operators.

---

## Glossary

- **Orchestrator**: The central routing engine that reads lead state, applies routing rules, dispatches tasks to agents, and processes outcomes.
- **Cold_Calling_Agent**: The agent responsible for initiating outbound AI-driven phone calls to new or re-engaged leads.
- **Follow_Up_Agent**: The agent responsible for re-engaging leads that did not respond to initial outreach.
- **Demo_Scheduling_Agent**: The agent responsible for coordinating calendar availability and booking product demos.
- **Auto_Mail_Agent**: The agent responsible for sending templated and AI-personalized outbound emails.
- **Auto_Reply_Agent**: The agent responsible for monitoring inbound emails, classifying intent, and sending contextual replies.
- **Call_Answering_Agent**: The agent responsible for handling inbound calls, qualifying callers, and routing to humans when needed.
- **Lead**: A prospect record containing contact information, status, interaction history, and scheduling data.
- **LeadStatus**: The enumerated pipeline stage of a lead: `new`, `contacted`, `interested`, `follow_up_scheduled`, `demo_scheduled`, `demo_completed`, `converted`, `not_interested`, `unsubscribed`, `do_not_contact`.
- **AgentTask**: A unit of work dispatched to an agent, containing lead reference, action type, priority, and retry metadata.
- **InteractionLog**: An append-only record of every touchpoint between the system and a lead.
- **Booking**: A confirmed or pending demo appointment linked to a lead and a calendar event.
- **Intent**: A classified signal extracted from a lead's message or call: `interested`, `not_interested`, `question`, `objection`, `callback_requested`, `meeting_request`, `unsubscribe`, `unknown`.
- **Task_Queue**: The distributed async queue (e.g., BullMQ) through which the Orchestrator dispatches tasks to agents.
- **Notification_Service**: The component responsible for routing alerts, escalations, and system events to the dashboard and external channels.
- **Dashboard**: The web-based operator interface for monitoring pipeline health, agent status, and lead activity.
- **DNC_List**: The do-not-call registry that must be checked before every outbound call action.
- **LLM_Service**: The large language model service used for conversation, NLP, and content personalization.
- **Telephony_API**: The external provider used for outbound and inbound call handling (e.g., Twilio, Bland AI).
- **Calendar_API**: The external provider used for slot availability and booking management (e.g., Google Calendar, Calendly).
- **Email_Provider**: The external service used for email delivery and tracking (e.g., SendGrid, AWS SES).
- **WebSocket_Server**: The server-side component that pushes real-time events to connected dashboard clients.

---

## Requirements

### Requirement 1: Orchestrator Lead Routing

**User Story:** As a sales operations manager, I want the Orchestrator to automatically route leads to the correct agent based on their current status and history, so that every lead receives the right outreach at the right time without manual intervention.

#### Acceptance Criteria

1. WHEN the Orchestrator evaluates a lead with `status = 'new'` and `call_attempts < config.maxColdCallAttempts`, THE Orchestrator SHALL dispatch a task to the Cold_Calling_Agent with action `call`.
2. WHEN the Orchestrator evaluates a lead with `status = 'new'` and `call_attempts >= config.maxColdCallAttempts`, THE Orchestrator SHALL dispatch a task to the Auto_Mail_Agent with action `send_intro_email`.
3. WHEN the Orchestrator evaluates a lead with `status = 'contacted'` and `hoursSince(last_contacted_at) >= config.followUpDelayHours`, THE Orchestrator SHALL dispatch a task to the Follow_Up_Agent with action `follow_up`.
4. WHEN the Orchestrator evaluates a lead with `status = 'interested'`, THE Orchestrator SHALL dispatch a task to the Demo_Scheduling_Agent with action `schedule_demo`.
5. WHEN the Orchestrator evaluates a lead with `status = 'demo_scheduled'` and `hoursUntil(demo_scheduled_at) <= 24`, THE Orchestrator SHALL dispatch a task to the Demo_Scheduling_Agent with action `send_reminder`.
6. WHEN the Orchestrator evaluates a lead with `status = 'do_not_contact'` OR `status = 'unsubscribed'`, THE Orchestrator SHALL return NULL and dispatch no task.
7. WHEN a lead's `last_contacted_at` is within `config.cooldownMinutes` of the current time, THE Orchestrator SHALL skip that lead and dispatch no task.
8. WHEN a lead's `last_contacted_at` is NULL, THE Orchestrator SHALL treat the lead as not on cooldown and proceed with evaluation.
9. THE Orchestrator SHALL persist every task outcome to the database by updating the lead's status, `last_contacted_at`, and `next_action_at` fields.
10. THE Orchestrator SHALL poll for leads pending action at an interval defined by `config.orchestratorPollIntervalSeconds`.

---

### Requirement 2: Cold Calling Agent

**User Story:** As a sales representative, I want the Cold Calling Agent to autonomously initiate and handle outbound AI-driven calls, so that new leads are contacted without requiring manual dialing.

#### Acceptance Criteria

1. WHEN the Cold_Calling_Agent receives a call task for a lead whose phone number is on the DNC_List, THE Cold_Calling_Agent SHALL update the lead status to `do_not_contact` and return a `blocked` outcome without initiating a call.
2. WHEN the Cold_Calling_Agent receives a call task outside of configured calling hours for the lead's timezone, THE Cold_Calling_Agent SHALL return a `deferred` outcome without initiating a call.
3. WHEN the Telephony_API returns a `no_answer` or `busy` status, THE Cold_Calling_Agent SHALL increment `call_attempts` on the lead and return a `no_answer` outcome.
4. WHEN the Telephony_API returns a `voicemail` status, THE Cold_Calling_Agent SHALL leave a voicemail using the configured script and return a `voicemail` outcome.
5. WHEN a call is answered, THE Cold_Calling_Agent SHALL run an AI conversation using the configured call script and extract intent from the transcript.
6. WHEN the extracted intent from a completed call is `interested`, THE Cold_Calling_Agent SHALL update the lead status to `interested`.
7. WHEN the extracted intent from a completed call is `not_interested`, THE Cold_Calling_Agent SHALL update the lead status to `not_interested`.
8. WHEN the extracted intent from a completed call is neither `interested` nor `not_interested`, THE Cold_Calling_Agent SHALL update the lead status to `contacted`.
9. THE Cold_Calling_Agent SHALL log every call interaction to the InteractionLog including transcript, intent, duration, and outcome.
10. WHEN the Telephony_API fails or times out during call initiation, THE Cold_Calling_Agent SHALL mark the task as `failed`, increment the retry counter, and schedule a retry with exponential backoff.

---

### Requirement 3: Follow-up Agent

**User Story:** As a sales manager, I want the Follow-up Agent to re-engage unresponsive leads through alternating channels, so that no lead is abandoned after a single touchpoint.

#### Acceptance Criteria

1. WHEN the Follow_Up_Agent executes a follow-up and the lead's total attempts (`email_attempts + call_attempts`) have reached `config.maxTotalFollowUpAttempts`, THE Follow_Up_Agent SHALL update the lead status to `not_interested` and escalate to the human review queue.
2. WHEN the last interaction with a lead was via `call`, THE Follow_Up_Agent SHALL select `email` as the follow-up channel.
3. WHEN the last interaction with a lead was via `email` and the lead has a non-null `phone`, THE Follow_Up_Agent SHALL select `call` as the follow-up channel.
4. WHEN the last interaction with a lead was via `email` and the lead has a null `phone`, THE Follow_Up_Agent SHALL select `email` as the follow-up channel.
5. WHEN no prior interaction exists for a lead, THE Follow_Up_Agent SHALL select `call` as the default follow-up channel.
6. THE Follow_Up_Agent SHALL personalize follow-up content using the lead's prior interaction context and the LLM_Service.
7. THE Follow_Up_Agent SHALL log every follow-up interaction to the InteractionLog including channel, outcome, and summary.

---

### Requirement 4: Demo Scheduling Agent

**User Story:** As a sales representative, I want the Demo Scheduling Agent to automatically coordinate calendar availability and book demos with interested leads, so that scheduling friction is eliminated.

#### Acceptance Criteria

1. WHEN the Demo_Scheduling_Agent is dispatched to schedule a demo, THE Demo_Scheduling_Agent SHALL fetch available slots from the Calendar_API within `config.schedulingWindowDays` days from the current time.
2. WHEN available slots are fetched, THE Demo_Scheduling_Agent SHALL offer the top `config.maxSlotsToOffer` slots to the lead via email and update the lead status to `follow_up_scheduled`.
3. WHEN no available slots exist in the scheduling window, THE Demo_Scheduling_Agent SHALL notify the admin via the Notification_Service and take no further action.
4. WHEN a lead confirms a slot, THE Demo_Scheduling_Agent SHALL create a calendar event via the Calendar_API, save a Booking record with status `confirmed`, update the lead status to `demo_scheduled`, and send a confirmation email via the Auto_Mail_Agent.
5. WHEN a booked slot becomes unavailable before confirmation, THE Demo_Scheduling_Agent SHALL notify the lead of the conflict, re-fetch available slots, and send an updated slot proposal.
6. WHEN a demo is within 24 hours of its scheduled time, THE Demo_Scheduling_Agent SHALL send a reminder email to the lead via the Auto_Mail_Agent.
7. WHEN a demo is within 1 hour of its scheduled time, THE Demo_Scheduling_Agent SHALL send a second reminder email to the lead via the Auto_Mail_Agent.
8. WHEN a lead requests a reschedule, THE Demo_Scheduling_Agent SHALL update the Booking status to `rescheduled`, fetch new available slots, and send an updated slot proposal.
9. THE Demo_Scheduling_Agent SHALL log all scheduling interactions to the InteractionLog.

---

### Requirement 5: Auto Mail Sending Agent

**User Story:** As a marketing operator, I want the Auto Mail Agent to send personalized outbound emails at scheduled times and track engagement, so that email outreach is automated and measurable.

#### Acceptance Criteria

1. THE Auto_Mail_Agent SHALL personalize the subject and body of every outbound email using lead data and the LLM_Service, replacing all template variable placeholders with lead-specific values.
2. WHEN personalizing an email, THE Auto_Mail_Agent SHALL produce output that contains no unresolved template variable placeholders.
3. WHEN an email is sent, THE Auto_Mail_Agent SHALL log the send event to the InteractionLog with the template name, subject, and timestamp.
4. WHEN an email open event is received via webhook, THE Auto_Mail_Agent SHALL update the corresponding InteractionLog entry with the open timestamp.
5. WHEN an email click event is received via webhook, THE Auto_Mail_Agent SHALL update the corresponding InteractionLog entry with the click timestamp and URL.
6. WHEN an unsubscribe event is received, THE Auto_Mail_Agent SHALL update the lead status to `unsubscribed` and add the lead's email to the suppression list.
7. WHEN the Email_Provider returns a delivery failure, THE Auto_Mail_Agent SHALL mark the task as `failed` and schedule a retry with exponential backoff.
8. WHILE a lead has `status = 'unsubscribed'`, THE Auto_Mail_Agent SHALL not send any outbound email to that lead.

---

### Requirement 6: Auto Reply Agent

**User Story:** As a sales operator, I want the Auto Reply Agent to automatically respond to inbound emails with contextually appropriate replies, so that leads receive timely responses without human intervention.

#### Acceptance Criteria

1. WHEN an inbound email is received from a sender that matches an existing lead record, THE Auto_Reply_Agent SHALL retrieve the lead's full interaction history before generating a reply.
2. WHEN an inbound email is received from a sender with no matching lead record, THE Auto_Reply_Agent SHALL create a new lead record with `source = 'inbound_email'` and proceed with reply generation.
3. WHEN the classified intent of an inbound message is `unsubscribe`, THE Auto_Reply_Agent SHALL update the lead status to `unsubscribed` and send an unsubscribe confirmation reply without generating an LLM response.
4. WHEN the LLM_Service confidence score for a classified intent is below `config.autoReplyConfidenceThreshold`, THE Auto_Reply_Agent SHALL escalate the message to the human review queue without sending an automated reply.
5. WHEN the confidence score meets or exceeds the threshold, THE Auto_Reply_Agent SHALL generate a contextual reply using the LLM_Service and send it via the Email_Provider.
6. THE Auto_Reply_Agent SHALL classify every inbound message into one of the defined Intent values: `interested`, `not_interested`, `question`, `objection`, `callback_requested`, `meeting_request`, `unsubscribe`, or `unknown`.
7. THE Auto_Reply_Agent SHALL log every inbound message and outbound reply to the InteractionLog with the classified intent and confidence score.
8. WHEN an automated reply is sent, THE Auto_Reply_Agent SHALL notify the Orchestrator with the lead ID and classified intent for downstream routing.

---

### Requirement 7: Call Answering Agent

**User Story:** As a sales operator, I want the Call Answering Agent to handle inbound calls autonomously, so that no inbound lead inquiry goes unanswered outside of business hours.

#### Acceptance Criteria

1. WHEN an inbound call is received, THE Call_Answering_Agent SHALL answer the call and run an AI-driven qualification conversation using the configured knowledge base.
2. WHEN a caller explicitly requests to speak with a human, THE Call_Answering_Agent SHALL transfer the call to the human representative queue.
3. WHEN the AI qualification conversation cannot determine the caller's intent with sufficient confidence, THE Call_Answering_Agent SHALL transfer the call to the human representative queue.
4. THE Call_Answering_Agent SHALL log the full call transcript, qualification outcome, and caller information to the InteractionLog after every call.
5. WHEN a caller's phone number matches an existing lead record, THE Call_Answering_Agent SHALL retrieve the lead's interaction history before beginning the qualification conversation.
6. WHEN a caller's phone number does not match any existing lead record, THE Call_Answering_Agent SHALL create a new lead record with `source = 'inbound_call'` after the call.

---

### Requirement 8: Lead Lifecycle and Data Integrity

**User Story:** As a system administrator, I want lead status transitions to be consistent and all agent actions to be fully auditable, so that the pipeline state is always trustworthy and recoverable.

#### Acceptance Criteria

1. THE System SHALL ensure that lead status transitions only progress forward through the defined LeadStatus pipeline unless an explicit reset action is performed by an operator.
2. THE System SHALL write every agent action to an append-only InteractionLog that cannot be modified after creation.
3. WHEN any agent is about to perform an outbound action, THE System SHALL verify the lead's status is not `do_not_contact` or `unsubscribed` before dispatching the task.
4. WHEN an AgentTask fails after `config.maxTaskRetries` retry attempts, THE System SHALL mark the task as `permanently_failed`, update the lead status to `requires_human_review`, and surface the lead in the dashboard escalation queue.
5. THE System SHALL encrypt all lead PII (phone, email, name) at rest in the database and in transit via TLS.
6. WHEN an inbound webhook request is received, THE System SHALL verify the HMAC signature before processing the payload and reject requests with invalid signatures.
7. THE System SHALL include system-level guardrails in all LLM prompts to prevent prompt injection via inbound lead message content.

---

### Requirement 9: Task Queue and Agent Reliability

**User Story:** As a platform engineer, I want agent tasks to be reliably queued, retried on failure, and independently scalable, so that the system handles high lead volumes without data loss.

#### Acceptance Criteria

1. THE Orchestrator SHALL dispatch all agent tasks through the Task_Queue to enable async processing and horizontal scaling.
2. WHEN an agent task fails, THE System SHALL retry the task up to `config.maxTaskRetries` times using exponential backoff.
3. THE System SHALL support independent horizontal scaling of each agent by processing tasks from the Task_Queue concurrently.
4. WHEN the LLM_Service is unreachable, THE System SHALL pause agent execution, log an alert to the Notification_Service, and queue tasks for retry when the service recovers.
5. WHEN the LLM_Service is unavailable and a static fallback script is configured, THE System SHALL fall back to the static script template for call and reply generation.

---

### Requirement 10: Dashboard — Overview and KPIs

**User Story:** As a sales operations manager, I want a real-time dashboard showing pipeline health and agent activity, so that I can monitor the system's performance at a glance.

#### Acceptance Criteria

1. THE Dashboard SHALL display four KPI metric cards: Calls Made, Emails Sent, Demos Scheduled, and Conversion Rate, each showing the current period value, trend percentage versus the prior period, and a 7-day sparkline.
2. THE Dashboard SHALL display one agent status card per agent (6 total) showing the agent's current status (`active`, `paused`, or `error`), queue depth, tasks completed today, and last action timestamp.
3. WHEN an agent's status is `active`, THE Dashboard SHALL display a pulsing green status indicator on that agent's card.
4. WHEN an agent's status is `error`, THE Dashboard SHALL display a red status indicator and show an error message snippet on that agent's card.
5. THE Dashboard SHALL display a pipeline funnel showing the count of leads at each LeadStatus stage.
6. THE Dashboard SHALL display a real-time activity feed showing the last 50 system events, with each event showing the timestamp, agent name, action description, and outcome.
7. WHEN a new system event occurs, THE Dashboard SHALL prepend it to the activity feed without requiring a page refresh.

---

### Requirement 11: Dashboard — Lead Management

**User Story:** As a sales representative, I want to view, filter, and manage all leads from a central table and kanban view, so that I can efficiently work my pipeline.

#### Acceptance Criteria

1. THE Dashboard SHALL display all leads in a sortable, filterable table with columns for name, company, status, last contacted, next action, assigned agent, call attempts, and email attempts.
2. WHEN a user applies one or more filters (status, source, assigned agent, date range), THE Dashboard SHALL display only leads that match all applied filter criteria.
3. WHEN a user enters a search query, THE Dashboard SHALL perform full-text search across lead name, email, and company fields and display only matching results, with matched text highlighted.
4. THE Dashboard SHALL support a kanban view where each column represents a LeadStatus value and leads can be dragged between columns to update their status.
5. WHEN a lead is dragged to a new kanban column, THE Dashboard SHALL optimistically update the lead's status in the UI and persist the change via an API call, rolling back with an error toast if the API call fails.
6. WHEN one or more leads are selected, THE Dashboard SHALL display bulk action controls for reassigning agent, changing status, exporting to CSV, marking as Do Not Contact, and deleting.
7. WHEN a bulk action is applied, THE System SHALL apply the action to all selected leads.
8. WHEN a user clicks a lead row or card, THE Dashboard SHALL open the lead's Interaction Timeline in a slide-over panel without navigating away from the leads view.

---

### Requirement 12: Dashboard — Agent Control Panel

**User Story:** As a sales operations manager, I want to monitor and control each agent's task queue and configuration, so that I can intervene when agents need attention.

#### Acceptance Criteria

1. THE Dashboard SHALL display a dedicated control panel for each agent showing queue depth, running tasks, tasks completed today, and tasks failed today.
2. WHEN an operator clicks the Pause button for an agent, THE System SHALL stop dispatching new tasks to that agent and update the agent's status to `paused`.
3. WHEN an operator clicks the Resume button for a paused agent, THE System SHALL resume dispatching tasks to that agent and update the agent's status to `active`.
4. THE Dashboard SHALL display the live task queue for each agent, sorted by priority, showing lead name, company, scheduled time, and attempt count for each task.
5. WHEN an operator cancels a queued task, THE System SHALL remove the task from the queue after displaying a confirmation prompt.
6. THE Dashboard SHALL display the last 20 completed tasks for each agent with their outcome badges.
7. WHEN an operator opens the agent configuration panel, THE Dashboard SHALL display editable fields for max attempts, cooldown windows, calling hours, and confidence thresholds.

---

### Requirement 13: Dashboard — Interaction Timeline

**User Story:** As a sales representative, I want to view the complete interaction history for any lead, so that I have full context before any manual follow-up.

#### Acceptance Criteria

1. THE Dashboard SHALL display a chronological timeline of all interactions for a lead, with the most recent event at the top.
2. WHEN a timeline event is a call, THE Dashboard SHALL display the agent name, timestamp, call duration, outcome badge, AI-generated summary, and controls to play the recording and expand the full transcript.
3. WHEN a timeline event is an email, THE Dashboard SHALL display the agent name, timestamp, subject line, and open/click status badges.
4. WHEN a timeline event is a demo booking, THE Dashboard SHALL display the scheduled date and time, booking status, and meeting link.
5. THE Dashboard SHALL display an editable notes field for each lead that auto-saves on blur.
6. THE Dashboard SHALL display editable status and tags fields for each lead that persist changes via API call on change.

---

### Requirement 14: Dashboard — Demo Scheduling View

**User Story:** As a sales representative, I want a calendar view of all scheduled demos, so that I can manage my demo pipeline and send reminders efficiently.

#### Acceptance Criteria

1. THE Dashboard SHALL display all scheduled demos in a calendar view (react-big-calendar) with week view as the default.
2. WHEN a demo event is displayed on the calendar, THE Dashboard SHALL color-code it by booking status: blue for `confirmed`, amber for `pending`, and red with strikethrough for `cancelled`.
3. WHEN a user clicks a demo event on the calendar, THE Dashboard SHALL open a booking detail slide-over showing lead name, company, date, time, status, meeting link, and action buttons.
4. WHEN an operator clicks "Send Reminder" in the booking detail panel, THE System SHALL immediately trigger a reminder email to the lead via the Auto_Mail_Agent and display a confirmation toast.
5. WHEN an operator clicks "Reschedule" in the booking detail panel, THE System SHALL open a slot picker that fetches live calendar availability and allows the operator to select a new time.
6. THE Dashboard SHALL display an upcoming demos list grouped by day showing lead name, company, time, and status badge.

---

### Requirement 15: Dashboard — Analytics and Reporting

**User Story:** As a sales manager, I want analytics charts showing pipeline conversion rates and agent performance, so that I can identify bottlenecks and optimize the sales process.

#### Acceptance Criteria

1. THE Dashboard SHALL display a full-width conversion funnel chart showing lead counts and conversion rates between each consecutive LeadStatus stage.
2. WHEN a user clicks a stage in the conversion funnel, THE Dashboard SHALL filter the Lead Management view to show only leads at that status.
3. THE Dashboard SHALL display an agent performance section showing tasks completed per agent per day as a bar chart and a summary table with success rate, average response time, and escalation count.
4. THE Dashboard SHALL display email metrics over time including open rate, click rate, and reply rate as a line chart, plus summary cards for total sent, average open rate, average click rate, and unsubscribe count.
5. THE Dashboard SHALL display a call outcomes donut chart showing the distribution of call outcomes (interested, not interested, voicemail, no answer, callback requested).
6. THE Dashboard SHALL display a lead source breakdown chart showing lead counts by source with conversion rate overlay.
7. WHEN a user selects a date range, THE Dashboard SHALL update all analytics charts and summary cards to reflect data within the selected range.
8. WHEN a user clicks "Export CSV" or "Export PDF", THE Dashboard SHALL generate and download a report containing the currently displayed analytics data.

---

### Requirement 16: Dashboard — Notification Center

**User Story:** As a sales operator, I want a notification center that surfaces escalations and system alerts, so that I can respond to issues that require human attention.

#### Acceptance Criteria

1. THE Dashboard SHALL display a notification center accessible from the topbar bell icon as a slide-over panel, without navigating away from the current page.
2. THE Dashboard SHALL display an unread notification count badge on the topbar bell icon when unread notifications exist.
3. THE Notification_Service SHALL categorize notifications into types: Escalation, Error, Success, Reminder, and System.
4. WHEN a new notification is created, THE Dashboard SHALL increment the unread badge count and prepend the notification to the notification panel without requiring a page refresh.
5. THE Dashboard SHALL display an escalation queue tab showing all leads and interactions flagged for human review, with columns for lead name, reason, escalating agent, time, and action buttons (Review, Dismiss, Reassign).
6. WHEN an operator clicks "Review" on an escalated item, THE Dashboard SHALL open the Interaction Timeline for that lead in a modal.
7. THE Dashboard SHALL support per-notification-type settings for in-app delivery, email digest (daily or weekly), and Slack webhook delivery.

---

### Requirement 17: Real-Time Updates via WebSocket

**User Story:** As a dashboard user, I want the UI to update in real time without manual refresh, so that I always see the current state of the pipeline and agents.

#### Acceptance Criteria

1. THE Dashboard SHALL maintain a WebSocket connection to the WebSocket_Server and receive real-time push events for agent status changes, task completions, task failures, lead status changes, new notifications, and KPI updates.
2. WHEN a `agent.status_changed` event is received, THE Dashboard SHALL update the corresponding agent status card immediately.
3. WHEN a `task.completed` event is received, THE Dashboard SHALL increment the agent's completion counter and append the event to the activity feed.
4. WHEN a `lead.status_changed` event is received, THE Dashboard SHALL update the lead's row in the table if it is currently visible, without triggering a full data re-fetch.
5. WHEN a `kpi.updated` event is received, THE Dashboard SHALL animate the KPI card numbers from their previous values to the new values over 600ms.
6. WHEN the WebSocket connection is lost, THE Dashboard SHALL display a "Reconnecting..." banner and attempt to reconnect using exponential backoff starting at 1 second, doubling each attempt up to a maximum of 30 seconds.
7. WHEN the WebSocket connection is restored, THE Dashboard SHALL dismiss the reconnecting banner and perform a full data refresh to reconcile any missed events.

---

### Requirement 18: UI Accessibility and Navigation

**User Story:** As a dashboard user, I want the interface to be fully keyboard-navigable and accessible, so that I can use the system efficiently regardless of input method.

#### Acceptance Criteria

1. THE Dashboard SHALL make all interactive elements reachable via the `Tab` key in a logical order.
2. WHEN a user presses `⌘K` or `Ctrl+K`, THE Dashboard SHALL open a global command palette that searches across leads, agents, interactions, and documentation.
3. WHEN a user presses `Escape`, THE Dashboard SHALL close any open modal, slide-over, or dropdown.
4. THE Dashboard SHALL display a visible focus ring (`2px solid --accent-blue` with `2px offset`) on all focused interactive elements in both light and dark themes.
5. THE Dashboard SHALL never use color as the sole indicator of state — every status indicator SHALL be paired with a text label or icon.
6. THE Dashboard SHALL support a dark theme (default) and a light theme, togglable via user settings, with the preference persisted in user account settings.
7. THE Dashboard SHALL display skeleton loading states matching the page structure while data is loading, rather than a generic spinner.
8. WHEN an API call fails, THE Dashboard SHALL display a user-friendly error message and never expose raw error codes or stack traces in the UI.
