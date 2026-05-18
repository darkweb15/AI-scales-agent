"use client";
import { Phone, Mail, Calendar, CheckCircle2, ArrowUpRight } from "lucide-react";

const items = [
  { icon: Phone,        color: "#6366F1", bg: "#EEF2FF", title: "Call Completed",  desc: "Arjun called Sarah Johnson",       time: "2m ago" },
  { icon: Mail,         color: "#10B981", bg: "#ECFDF5", title: "Email Sent",       desc: "Priya sent follow-up to DataSoft", time: "7m ago" },
  { icon: Calendar,     color: "#F59E0B", bg: "#FFFBEB", title: "Demo Scheduled",   desc: "Rahul booked demo with Acme Corp", time: "15m ago" },
  { icon: CheckCircle2, color: "#8B5CF6", bg: "#F5F3FF", title: "Lead Converted",   desc: "Sneha converted NexGen AI",        time: "32m ago" },
  { icon: Mail,         color: "#06B6D4", bg: "#ECFEFF", title: "Auto Reply Sent",  desc: "AI replied to Mike Chen",          time: "45m ago" },
  { icon: Phone,        color: "#6366F1", bg: "#EEF2FF", title: "Call Completed",   desc: "Karan called James Wilson",        time: "1h ago" },
];

export default function RecentActivities() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-gray-100">
        <div>
          <h2 className="text-sm font-bold text-gray-900">Recent Activities</h2>
          <p className="text-[11px] text-gray-400 mt-0.5">All agents</p>
        </div>
        <button className="flex items-center gap-1 text-xs font-semibold text-indigo-600">
          View All Activities <ArrowUpRight size={11} />
        </button>
      </div>
      <div className="divide-y divide-gray-50">
        {items.map(({ icon: Icon, color, bg, title, desc, time }, i) => (
          <div key={i} className="flex items-start gap-3 px-5 py-2.5 hover:bg-gray-50 transition-colors cursor-pointer">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5" style={{ backgroundColor: bg }}>
              <Icon size={13} style={{ color }} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-semibold text-gray-800">{title}</span>
                <span className="text-[10px] text-gray-400 shrink-0">{time}</span>
              </div>
              <p className="text-[11px] text-gray-500 mt-0.5 truncate">{desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
