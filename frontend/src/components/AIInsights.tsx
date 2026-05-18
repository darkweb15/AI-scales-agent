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
      icon: Clock, color: "#4F8EF7", bg: "#4F8EF715",
      title: "Best Time to Call",
      desc: "Today between 10:00 AM – 12:00 PM for highest connect rate",
      sub: "1.3x higher connect rate",
    },
    {
      icon: Users, color: "#34D399", bg: "#34D39915",
      title: `${interested} Hot Leads`,
      desc: `${interested} leads showing high intent — ready for demo`,
      sub: "Schedule demos now",
    },
    {
      icon: MessageSquare, color: "#FBBF24", bg: "#FBBF2415",
      title: `${followUp} Follow-ups Due`,
      desc: `${followUp} leads need follow-up today`,
      sub: "Take action",
    },
    {
      icon: TrendingUp, color: "#A78BFA", bg: "#A78BFA15",
      title: "Pipeline Health",
      desc: `${total} total leads · ${newLeads} new · ${interested} interested`,
      sub: "View full pipeline",
    },
  ];

  return (
    <div className="card overflow-hidden flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3.5 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-accent-purple to-accent-blue flex items-center justify-center">
            <Sparkles size={13} className="text-white" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-text-primary">AI Insights</h2>
            <p className="text-[10px] text-text-muted">Live from your database</p>
          </div>
        </div>
        <button className="flex items-center gap-1 text-xs font-semibold text-accent-blue">
          View All <ArrowUpRight size={11} />
        </button>
      </div>

      <div className="flex-1 p-3 space-y-2 overflow-y-auto">
        {insights.map(({ icon: Icon, color, bg, title, desc, sub }) => (
          <div key={title} className="flex items-start gap-2.5 p-2.5 rounded-lg hover:bg-bg-elevated transition-colors cursor-pointer">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5" style={{ backgroundColor: bg }}>
              <Icon size={13} style={{ color }} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-semibold text-text-primary mb-0.5">{title}</div>
              <p className="text-[11px] text-text-secondary leading-relaxed">{desc}</p>
              <p className="text-[10px] font-semibold mt-0.5" style={{ color }}>{sub}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="p-3 border-t border-border">
        <div className="flex items-center gap-2 bg-bg-elevated border border-border rounded-xl px-3 py-2 focus-within:border-accent-blue/50 transition-all">
          <Sparkles size={12} className="text-accent-purple shrink-0" />
          <input value={q} onChange={e => setQ(e.target.value)}
            placeholder="Ask AI about your sales..."
            className="bg-transparent text-xs text-text-primary placeholder-text-muted outline-none flex-1" />
          <button className={`w-6 h-6 rounded-lg flex items-center justify-center shrink-0 transition-colors ${q ? "bg-accent-blue text-white" : "bg-bg-subtle text-text-muted"}`}>
            <Send size={10} />
          </button>
        </div>
      </div>
    </div>
  );
}
