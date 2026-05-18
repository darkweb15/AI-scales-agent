"use client";
import { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { Download, TrendingUp, Users, Phone, Calendar } from "lucide-react";

const COLORS = ["#4F8EF7","#34D399","#FBBF24","#A78BFA","#F87171","#06B6D4"];

export default function AnalyticsPage() {
  const [collapsed, setCollapsed] = useState(false);
  const [leads, setLeads] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://localhost:8001/api/leads?limit=200")
      .then(r => r.json())
      .then(data => { setLeads(Array.isArray(data) ? data : []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  // Real funnel from actual leads
  const statusOrder = ["new","contacted","interested","follow_up_scheduled","demo_scheduled","demo_completed","converted"];
  const statusLabels: Record<string,string> = {
    new: "New Leads", contacted: "Contacted", interested: "Interested",
    follow_up_scheduled: "Follow-up", demo_scheduled: "Demo Scheduled",
    demo_completed: "Demo Done", converted: "Converted",
  };

  const funnelData = statusOrder.map(s => ({
    stage: statusLabels[s],
    count: leads.filter(l => l.status === s).length,
    pct: leads.length > 0 ? Math.round((leads.filter(l => l.status === s).length / leads.length) * 100) : 0,
  }));

  // Source breakdown
  const sources = leads.reduce((acc: any, l) => {
    const s = l.source || "unknown";
    acc[s] = (acc[s] || 0) + 1;
    return acc;
  }, {});
  const sourceData = Object.entries(sources).map(([name, value]) => ({ name, value }));

  const total = leads.length;
  const converted = leads.filter(l => l.status === "converted").length;
  const convRate = total > 0 ? ((converted / total) * 100).toFixed(1) : "0.0";
  const interested = leads.filter(l => l.status === "interested").length;
  const demos = leads.filter(l => l.status === "demo_scheduled" || l.status === "demo_completed").length;

  return (
    <div className="flex h-screen overflow-hidden bg-bg-base">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-5 space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-black text-text-primary">Analytics</h2>
              <p className="text-xs text-text-muted mt-0.5">Real data · {total} total leads</p>
            </div>
            <button className="flex items-center gap-1.5 bg-bg-elevated border border-border rounded-xl px-3 py-2 text-xs font-bold text-text-secondary hover:border-accent-blue/30 transition-all">
              <Download size={13} /> Export
            </button>
          </div>

          {/* Summary cards */}
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: "Total Leads",    val: total.toString(),    icon: Users,    color: "#4F8EF7", bg: "#4F8EF715" },
              { label: "Interested",     val: interested.toString(), icon: TrendingUp, color: "#34D399", bg: "#34D39915" },
              { label: "Demos",          val: demos.toString(),    icon: Calendar, color: "#FBBF24", bg: "#FBBF2415" },
              { label: "Conversion",     val: `${convRate}%`,      icon: Phone,    color: "#A78BFA", bg: "#A78BFA15" },
            ].map(({ label, val, icon: Icon, color, bg }) => (
              <div key={label} className="card p-4">
                <div className="w-9 h-9 rounded-xl flex items-center justify-center mb-3" style={{ backgroundColor: bg }}>
                  <Icon size={17} style={{ color }} />
                </div>
                <div className="text-2xl font-black text-text-primary">{val}</div>
                <div className="text-[11px] font-bold text-text-muted uppercase tracking-wide mt-0.5">{label}</div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-3 gap-5">
            {/* Real funnel */}
            <div className="col-span-2 card p-5">
              <h3 className="text-sm font-bold text-text-primary mb-4">Pipeline Funnel</h3>
              {loading ? (
                <div className="text-center py-8 text-sm text-text-muted">Loading...</div>
              ) : (
                <div className="space-y-2.5">
                  {funnelData.map(({ stage, count, pct }, i) => (
                    <div key={stage} className="flex items-center gap-3">
                      <div className="w-32 text-right text-xs font-semibold text-text-secondary shrink-0">{stage}</div>
                      <div className="flex-1 h-8 bg-bg-elevated rounded-lg overflow-hidden">
                        <div className="h-full rounded-lg flex items-center px-3 transition-all duration-700"
                          style={{ width: `${Math.max(pct, count > 0 ? 8 : 0)}%`, backgroundColor: COLORS[i] || "#94A3B8" }}>
                          <span className="text-xs font-extrabold text-white">{count}</span>
                        </div>
                      </div>
                      <div className="w-10 text-right text-xs font-bold shrink-0" style={{ color: COLORS[i] }}>{pct}%</div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Source breakdown */}
            <div className="card p-5">
              <h3 className="text-sm font-bold text-text-primary mb-4">Lead Sources</h3>
              {sourceData.length > 0 ? (
                <>
                  <ResponsiveContainer width="100%" height={150}>
                    <PieChart>
                      <Pie data={sourceData} cx="50%" cy="50%" innerRadius={40} outerRadius={65} dataKey="value">
                        {sourceData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="space-y-1.5 mt-2">
                    {sourceData.map(({ name, value }, i) => (
                      <div key={name} className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                          <span className="text-[11px] text-text-secondary font-medium capitalize">{name}</span>
                        </div>
                        <span className="text-[11px] font-bold text-text-primary">{value as number}</span>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="text-center py-8 text-sm text-text-muted">No data yet</div>
              )}
            </div>
          </div>

          {/* Status bar chart */}
          <div className="card p-5">
            <h3 className="text-sm font-bold text-text-primary mb-4">Leads by Status</h3>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={funnelData} margin={{ left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2A2A38" />
                <XAxis dataKey="stage" tick={{ fontSize: 9, fill: "#55556A" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: "#55556A" }} axisLine={false} tickLine={false} />
                <Tooltip />
                <Bar dataKey="count" radius={[4,4,0,0]}>
                  {funnelData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </main>
      </div>
    </div>
  );
}
