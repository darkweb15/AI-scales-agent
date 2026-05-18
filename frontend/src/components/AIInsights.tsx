"use client";
import { Sparkles, Clock, Users, MessageSquare, TrendingUp, ArrowUpRight, Send } from "lucide-react";
import { useState } from "react";

interface Props {
  leads?: any[];
}

export default function AIInsights({ leads = [] }: Props) {
  const [q, setQ] = useState("");

  const newLeads = leads.filter(l => l.status === "new").length;
  const interested = leads.filter(l => l.status === "interested").length;
  const followUp = leads.filter(l => l.status === "follow_up_scheduled").length;
  const total = leads.length;

  const insights = [
    {
      icon: Clock, color: "#6366F1", bg: "#EEF2FF",
      title: "Best Time to Call",
      desc: "Today between 10:00 AM – 12:00 PM for highest connect rate",
      sub: "1.3× higher connect rate",
    },
    {
      icon: Users, color: "#10B981", bg: "#ECFDF5",
      title: `${interested} Hot Leads`,
      desc: `${interested} leads showing high intent — ready for demo`,
      sub: "Schedule demos now →",
    },
    {
      icon: MessageSquare, color: "#F59E0B", bg: "#FFFBEB",
      title: `${followUp} Follow-ups Due`,
      desc: `${followUp} leads need follow-up today`,
      sub: "Take action →",
    },
    {
      icon: TrendingUp, color: "#8B5CF6", bg: "#F5F3FF",
      title: "Pipeline Health",
      desc: `${total} total leads · ${newLeads} new · ${interested} interested`,
      sub: "View full pipeline →",
    },
  ];

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3.5 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
            <Sparkles size={13} className="text-white" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-gray-900">AI Insights</h2>
            <p className="text-[10px] text-gray-400">Live from your database</p>
          </div>
        </div>
        <button className="flex items-center gap-1 text-xs font-semibold text-indigo-600">
          View All <ArrowUpRight size={11} />
        </button>
      </div>

      <div className="flex-1 p-3 space-y-2 overflow-y-auto">
        {insights.map(({ icon: Icon, color, bg, title, desc, sub }) => (
          <div key={title} className="flex items-start gap-2.5 p-2.5 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5" style={{ backgroundColor: bg }}>
              <Icon size={13} style={{ color }} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-semibold text-gray-800 mb-0.5">{title}</div>
              <p className="text-[11px] text-gray-500 leading-relaxed">{desc}</p>
              <p className="text-[10px] font-semibold mt-0.5" style={{ color }}>{sub}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="p-3 border-t border-gray-100">
        <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus-within:border-indigo-400 focus-within:bg-white transition-all">
          <Sparkles size={12} className="text-indigo-400 shrink-0" />
          <input value={q} onChange={e => setQ(e.target.value)}
            placeholder="Ask AI about your sales..."
            className="bg-transparent text-xs text-gray-700 placeholder-gray-400 outline-none flex-1" />
          <button className={`w-6 h-6 rounded-lg flex items-center justify-center shrink-0 transition-colors ${q ? "bg-indigo-600 text-white" : "bg-gray-200 text-gray-400"}`}>
            <Send size={10} />
          </button>
        </div>
      </div>
    </div>
  );
}
