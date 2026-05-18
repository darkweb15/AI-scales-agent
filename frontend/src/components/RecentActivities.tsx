"use client";
import { Phone, Mail, Calendar, CheckCircle2, ArrowUpRight } from "lucide-react";

const items = [
  { icon: Phone,        color: "#4F8EF7", bg: "#4F8EF715", title: "Call Completed",  desc: "Arjun called Sarah Johnson",       time: "2m ago" },
  { icon: Mail,         color: "#34D399", bg: "#34D39915", title: "Email Sent",       desc: "Priya sent follow-up to DataSoft", time: "7m ago" },
  { icon: Calendar,     color: "#FBBF24", bg: "#FBBF2415", title: "Demo Scheduled",   desc: "Rahul booked demo with Acme Corp", time: "15m ago" },
  { icon: CheckCircle2, color: "#A78BFA", bg: "#A78BFA15", title: "Lead Converted",   desc: "Sneha converted NexGen AI",        time: "32m ago" },
  { icon: Mail,         color: "#34D399", bg: "#34D39915", title: "Auto Reply Sent",  desc: "AI replied to Mike Chen",          time: "45m ago" },
  { icon: Phone,        color: "#4F8EF7", bg: "#4F8EF715", title: "Call Completed",   desc: "Karan called James Wilson",        time: "1h ago" },
];

export default function RecentActivities() {
  return (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-border">
        <div>
          <h2 className="text-sm font-bold text-text-primary">Recent Activities</h2>
          <p className="text-[11px] text-text-muted mt-0.5">All agents</p>
        </div>
        <button className="flex items-center gap-1 text-xs font-semibold text-accent-blue">
          View All Activities <ArrowUpRight size={11} />
        </button>
      </div>
      <div className="divide-y divide-border/50">
        {items.map(({ icon: Icon, color, bg, title, desc, time }, i) => (
          <div key={i} className="flex items-start gap-3 px-5 py-2.5 hover:bg-bg-elevated transition-colors cursor-pointer">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5" style={{ backgroundColor: bg }}>
              <Icon size={13} style={{ color }} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-semibold text-text-primary">{title}</span>
                <span className="text-[10px] text-text-muted shrink-0">{time}</span>
              </div>
              <p className="text-[11px] text-text-secondary mt-0.5 truncate">{desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
