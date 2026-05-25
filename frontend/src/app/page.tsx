"use client";
import { useState, useEffect, useCallback } from "react";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import KPICards from "@/components/KPICards";
import AgentPerformance from "@/components/AgentPerformance";
import AIInsights from "@/components/AIInsights";
import ActivityOverview from "@/components/ActivityOverview";
import TopAgents from "@/components/TopAgents";
import RecentActivities from "@/components/RecentActivities";
import AIAssistantBar from "@/components/AIAssistantBar";
import { useWebSocket } from "@/hooks/useWebSocket";

export default function DashboardPage() {
  const [collapsed, setCollapsed] = useState(false);
  const [stats, setStats] = useState<any>(null);
  const [leads, setLeads] = useState<any[]>([]);
  const { connected, lastEvent } = useWebSocket("ws://localhost:8001/api/ws/dashboard");

  const fetchData = useCallback(() => {
    Promise.all([
      fetch("http://localhost:8001/api/business/stats").then(r => r.json()).catch(() => null),
      fetch("http://localhost:8001/api/leads?limit=200").then(r => r.json()).catch(() => []),
    ]).then(([bizStats, leadsData]) => {
      setStats(bizStats);
      setLeads(Array.isArray(leadsData) ? leadsData : []);
    });
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Re-fetch when WebSocket broadcasts a relevant event
  useEffect(() => {
    if (lastEvent && ["lead_updated", "lead_created", "agent_action", "orchestrator_tick"].includes(lastEvent.event_type)) {
      fetchData();
    }
  }, [lastEvent, fetchData]);

  // Count leads by status
  const statusCounts = leads.reduce((acc: any, l: any) => {
    acc[l.status] = (acc[l.status] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "#F8F9FC" }}>
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-5 pb-20 space-y-5">
          <KPICards stats={stats} totalLeads={leads.length} statusCounts={statusCounts} />

          {/* Business Data Banner */}
          {stats && (
            <div className="bg-gradient-to-r from-indigo-600 to-violet-600 rounded-xl p-4 text-white flex items-center justify-between">
              <div>
                <div className="text-base font-black">📊 Business Database Connected</div>
                <div className="text-indigo-200 text-xs mt-0.5">
                  {stats.total_records?.toLocaleString()} total records · {stats.with_phone?.toLocaleString()} phone numbers · {stats.with_address?.toLocaleString()} addresses
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="text-center">
                  <div className="text-xl font-black">{leads.length}</div>
                  <div className="text-indigo-200 text-[10px] uppercase tracking-wide">In Pipeline</div>
                </div>
                <a href="/business" className="bg-white text-indigo-600 text-xs font-bold px-4 py-2 rounded-xl hover:bg-indigo-50 transition-colors">
                  View Analytics →
                </a>
              </div>
            </div>
          )}
          <div className="grid grid-cols-5 gap-5">
            <div className="col-span-3"><AgentPerformance /></div>
            <div className="col-span-2"><AIInsights leads={leads} /></div>
          </div>
          <div className="grid grid-cols-3 gap-5">
            <div className="col-span-1"><ActivityOverview /></div>
            <div className="col-span-1"><TopAgents /></div>
            <div className="col-span-1"><RecentActivities /></div>
          </div>
        </main>
        <AIAssistantBar />
      </div>
    </div>
  );
}
