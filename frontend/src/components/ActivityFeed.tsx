"use client";

const events = [
  { agent: "Cold Calling",    action: "Called Sarah Johnson",       outcome: "interested",  time: "just now", color: "#4F46E5" },
  { agent: "Auto Mail",       action: "Sent intro to TechCorp Ltd", outcome: "sent",        time: "1m ago",   color: "#059669" },
  { agent: "Demo Scheduling", action: "Booked demo — Acme Inc",     outcome: "confirmed",   time: "3m ago",   color: "#0284C7" },
  { agent: "Auto Reply",      action: "Replied to Mike Chen",       outcome: "replied",     time: "5m ago",   color: "#7C3AED" },
  { agent: "Follow-up",       action: "Follow-up call — DataSoft",  outcome: "no_answer",   time: "8m ago",   color: "#D97706" },
  { agent: "Call Answering",  action: "Inbound +1 555 0192",        outcome: "transferred", time: "12m ago",  color: "#EA580C" },
  { agent: "Cold Calling",    action: "Called James Wilson",        outcome: "voicemail",   time: "15m ago",  color: "#4F46E5" },
  { agent: "Auto Mail",       action: "Follow-up — CloudBase",      outcome: "sent",        time: "18m ago",  color: "#059669" },
];

const badgeStyle: Record<string, { bg: string; text: string }> = {
  interested:  { bg: "#ECFDF5", text: "#059669" },
  sent:        { bg: "#EEF2FF", text: "#4F46E5" },
  confirmed:   { bg: "#F0F9FF", text: "#0284C7" },
  replied:     { bg: "#F5F3FF", text: "#7C3AED" },
  no_answer:   { bg: "#F8FAFC", text: "#64748B" },
  transferred: { bg: "#FFFBEB", text: "#D97706" },
  voicemail:   { bg: "#F8FAFC", text: "#64748B" },
};

export default function ActivityFeed() {
  return (
    <div className="bg-white rounded-2xl border-2 border-[#E2E8F0] shadow-md overflow-hidden h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b-2 border-[#F1F5F9]">
        <div>
          <h2 className="text-base font-black text-[#0F172A] tracking-tight">Live Activity</h2>
          <p className="text-xs text-[#94A3B8] font-semibold mt-0.5">Real-time agent events</p>
        </div>
        <span className="flex items-center gap-1.5 text-xs font-extrabold text-emerald-700 bg-emerald-50 border-2 border-emerald-200 px-2.5 py-1.5 rounded-full">
          <span className="w-2 h-2 rounded-full bg-emerald-500 pulse-dot" /> Live
        </span>
      </div>

      {/* Feed */}
      <div className="flex-1 overflow-y-auto divide-y divide-[#F8FAFC]">
        {events.map((e, i) => {
          const badge = badgeStyle[e.outcome] || { bg: "#F8FAFC", text: "#64748B" };
          return (
            <div key={i} className="flex items-start gap-3 px-5 py-3.5 hover:bg-[#FAFBFF] transition-colors cursor-pointer">
              {/* Colored dot */}
              <div className="mt-1.5 shrink-0">
                <span className="w-2.5 h-2.5 rounded-full block" style={{ backgroundColor: e.color }} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <span className="text-xs font-bold text-[#0F172A] leading-snug">{e.action}</span>
                  <span className="text-[10px] font-semibold text-[#94A3B8] shrink-0 mt-0.5">{e.time}</span>
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[10px] font-bold text-[#94A3B8]">{e.agent}</span>
                  <span
                    className="text-[10px] font-extrabold px-2 py-0.5 rounded-full"
                    style={{ backgroundColor: badge.bg, color: badge.text }}
                  >
                    {e.outcome}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className="px-5 py-3 border-t-2 border-[#F1F5F9] bg-[#FAFBFF]">
        <button className="text-xs font-extrabold text-indigo-600 hover:text-indigo-700 transition-colors">
          View all activity →
        </button>
      </div>
    </div>
  );
}
