import enum


class LeadStatus(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    interested = "interested"
    follow_up_scheduled = "follow_up_scheduled"
    demo_scheduled = "demo_scheduled"
    demo_completed = "demo_completed"
    converted = "converted"
    not_interested = "not_interested"
    unsubscribed = "unsubscribed"
    do_not_contact = "do_not_contact"
    requires_human_review = "requires_human_review"


# Ordered pipeline stages for monotonic progression validation
LEAD_STATUS_ORDER = [
    LeadStatus.new,
    LeadStatus.contacted,
    LeadStatus.interested,
    LeadStatus.follow_up_scheduled,
    LeadStatus.demo_scheduled,
    LeadStatus.demo_completed,
    LeadStatus.converted,
]

# Terminal statuses that are not part of the forward pipeline
TERMINAL_STATUSES = {
    LeadStatus.not_interested,
    LeadStatus.unsubscribed,
    LeadStatus.do_not_contact,
    LeadStatus.requires_human_review,
}


class AgentType(str, enum.Enum):
    cold_calling = "cold_calling"
    follow_up = "follow_up"
    demo_scheduling = "demo_scheduling"
    auto_mail = "auto_mail"
    auto_reply = "auto_reply"
    call_answering = "call_answering"


class Channel(str, enum.Enum):
    call = "call"
    email = "email"
    sms = "sms"


class Intent(str, enum.Enum):
    interested = "interested"
    not_interested = "not_interested"
    question = "question"
    objection = "objection"
    callback_requested = "callback_requested"
    meeting_request = "meeting_request"
    unsubscribe = "unsubscribe"
    unknown = "unknown"


class TaskStatus(str, enum.Enum):
    queued = "queued"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    retrying = "retrying"
    permanently_failed = "permanently_failed"


class BookingStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    rescheduled = "rescheduled"
    completed = "completed"


class Direction(str, enum.Enum):
    inbound = "inbound"
    outbound = "outbound"
