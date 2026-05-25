"use client";
import { useState, useEffect, useCallback } from "react";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import AddLeadModal from "@/components/AddLeadModal";
import { Phone, Mail, Calendar, MessageSquare, Inbox, PhoneIncoming, Pause, Play, AlertTriangle, Zap, RefreshCw } from "lucide-react";

const API = "http://localhost:8001";

const AGENT_META: Record<string, { name: string; icon: any; color: string; grad: string }> = {
  cold_calling:    { name: "Cold Calling",   icon: Phone,         color: "#6366F1", grad: "from-indigo-500 to-violet-600" },
  follow_up:       { name: "Follow-up",      icon: Mail,          color: "#10B981", grad: "from-emerald-500 to-teal-500" },
  demo_scheduling: { name: "Demo Scheduling", icon: Calendar,     color: "#0284C7", grad: "from-sky-500 to-cyan-500" },
  auto_mail:       { name: "Auto Mail",       icon: MessageSquare, color: "#D97706", grad: "from-amber-400 to-orange-500" },
  auto_reply:      { name: "Auto Reply",      icon: Inbox,         color: "#8B5CF6", grad: "from-violet-500 to-purple-600" },
  call_answering:  { name: "Call Answering",  icon: PhoneIncoming, color: "#DC2626", grad: "from-red-500 to-rose-600" },
};

interface AgentState {
  agent_type: string;
  status: string;
  queue: number;
  completed_today: number;
  failed_today: number;
  orchestrator_running: boolean;
}

interface AgentConfig {
  max_cold_call_attempts: number;
  cooldown_minutes: number;
  follow_up_delay_hours: number;
  calling_hours_start: number;
  calling_hours_end: number;
  auto_reply_confidence_threshold: number;
  max_task_retries: number;
}

export default function AgentsPage() {
  const [collapsed, setCollapsed] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [active, setActive] = useState("cold_calling");
  const [agents, setAgents] = useState<AgentState[]>([]);
  const [config, setConfig] = useState<AgentConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [configLoading, setConfigLoading] = useState(false);
  const [toast, setToast] = useState("");
  const [orchStatus, setOrchStatus] = useState<{ running: boolean; message: string } | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(""), 4000);
  };

  const fetchAgents = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/agents`);
      const data = await res.json();
      setAgents(Array.isArray(data) ? data : []);
    } catch {
      setAgents([]);
    }
    setLoading(false);
  }, []);

  const fetchConfig = useCallback(async (agentType: string) => {
    setConfigLoading(true);
    try {
      const res = await fetch(`${API}/api/agents/${agentType}/config`);
      const data = await res.json();
      setConfig(data);
    } catch {
      setConfig(null);
    }
    setConfigLoading(false);
  }, []);

  const fetchOrchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/agents/orchestrator/status`);
      const data = await res.json();
      setOrchStatus(data);
    } catch {
      setOrchStatus(null);
    }
  }, []);

  useEffect(() => {
    fetchAgents();
    fetchOrchStatus();
  }, [fetchAgents, fetchOrchStatus]);

  useEffect(() => {
    fetchConfig(active);
  }, [active, fetchConfig]);

  useEffect(() => {
    const interval = setInterval(() => { fetchAgents(); fetchOrchStatus(); }, 10000);
    return () => clearInterval(interval);
  }, [fetchAgents, fetchOrchStatus]);

  const pauseAgent = async (agentType: string) => {
    try {
      await fetch(`${API}/api/agents/${agentType}/pause`, { method: "POST" });
      showToast(`Paused ${AGENT_META[agentType]?.name || agentType}`);
      fetchAgents();
    } catch {
      showToast("Failed to pause agent");
    }
  };

  const resumeAgent = async (agentType: string) => {
    try {
      await fetch(`${API}/api/agents/${agentType}/resume`, { method: "POST" });
      showToast(`Resumed ${AGENT_META[agentType]?.name || agentType}`);
      fetchAgents();
    } catch {
      showToast("Failed to resume agent");
    }
  };

  const triggerAgent = async (agentType: string) => {
    try {
      const res = await fetch(`${API}/api/agents/${agentType}/trigger`, { method: "POST" });
      const data = await res.json();
      showToast(data.message || "Triggered!");
      fetchAgents();
    } catch {
      showToast("Failed to trigger agent");
    }
  };

  const saveConfig = async () => {
    if (!config) return;
    try {
      const res = await fetch(`${API}/api/agents/${active}/config`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      const data = await res.json();
      setConfig(data);
      showToast("Configuration saved!");
    } catch {
      showToast("Failed to save config");
    }
  };

  const toggleOrchestrator = async () => {
    const action = orchStatus?.running ? "stop" : "start";
    try {
      const res = await fetch(`${API}/api/agents/orchestrator/${action}`, { method: "POST" });
      const data = await res.json();
      showToast(data.message || `Orchestrator ${action}ed`);
      fetchOrchStatus();
    } catch {
      showToast(`Failed to ${action} orchestrator`);
    }
  };

  const agentState = agents.find(a => a.agent_type === active);
  const meta = AGENT_META[active] || { name: active, icon: Zap, color: "#6366F1", grad: "from-indigo-500 to-violet-600" };
  const Icon = meta.icon;
  const agentIds = Object.keys(AGENT_META);

  return (
    <div className="flex h-screen overflow-hidden bg-[#F8F9FC]">
      {showAddModal && <AddLeadModal onClose={() => setShowAddModal(false)} onAdded={() => {}} />}
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <Topbar onAddLead={() => setShowAddModal(true)} />
        <main className="flex-1 overflow-y-auto p-5">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-lg font-black text-gray-900">Agent Control Panel</h2>
              <p className="text-xs text-gray-400 mt-0.5">Monitor and control all AI agents — live data from backend</p>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => { fetchAgents(); fetchOrchStatus(); }}
                className="flex items-center gap-1.5 bg-white border border-gray-200 rounded-xl px-3 py-2 text-xs font-bold text-gray-600 hover:border-indigo-300 transition-all">
                <RefreshCw size={12} /> Refresh
              </button>
              <button onClick={toggleOrchestrator}
                className={`flex items-center gap-1.5 text-xs font-bold px-3 py-2 rounded-xl transition-all ${
                  orchStatus?.running
                    ? "bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100"
                    : "bg-red-50 text-red-700 border border-red-200 hover:bg-red-100"
                }`}>
                <span className={`w-2 h-2 rounded-full ${orchStatus?.running ? "bg-emerald-500" : "bg-red-500"}`} />
                Orchestrator {orchStatus?.running ? "Running" : "Stopped"}
              </button>
            </div>
          </div>

          {/* Agent tabs */}
          <div className="flex items-center gap-2 mb-5 flex-wrap">
            {agentIds.map(id => {
              const m = AGENT_META[id];
              const AIcon = m.icon;
              const st = agents.find(a => a.agent_type === id)?.status || "active";
              return (
                <button key={id} onClick={() => setActive(id)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold transition-all border ${
                    active === id ? "bg-indigo-600 text-white border-indigo-600 shadow-sm" : "bg-white text-gray-600 border-gray-200 hover:border-indigo-300"
                  }`}>
                  <AIcon size={13} />
                  {m.name}
                  <span className={`w-1.5 h-1.5 rounded-full ${st === "active" ? "bg-emerald-400" : st === "paused" ? "bg-amber-400" : "bg-red-500"}`} />
                </button>
              );
            })}
          </div>

          <div className="grid grid-cols-3 gap-5">
            {/* Agent detail */}
            <div className="col-span-2 space-y-4">
              {/* Header card */}
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${meta.grad} flex items-center justify-center shadow-md`}>
                      <Icon size={22} className="text-white" />
                    </div>
                    <div>
                      <h3 className="text-base font-black text-gray-900">{meta.name} Agent</h3>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className={`w-2 h-2 rounded-full ${agentState?.status === "active" ? "bg-emerald-500" : agentState?.status === "paused" ? "bg-amber-400" : "bg-red-500"}`} />
                        <span className={`text-xs font-bold ${agentState?.status === "active" ? "text-emerald-600" : agentState?.status === "paused" ? "text-amber-600" : "text-red-600"}`}>
                          {agentState?.status === "active" ? "Running" : agentState?.status === "paused" ? "Paused" : agentState?.status || "Loading..."}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {agentState?.status === "paused" ? (
                      <button onClick={() => resumeAgent(active)}
                        className="flex items-center gap-1.5 bg-emerald-500 text-white text-xs font-bold px-3 py-2 rounded-xl hover:bg-emerald-600 transition-colors">
                        <Play size={12} /> Resume
                      </button>
                    ) : (
                      <button onClick={() => pauseAgent(active)}
                        className="flex items-center gap-1.5 bg-gray-100 text-gray-600 text-xs font-bold px-3 py-2 rounded-xl hover:bg-gray-200 transition-colors">
                        <Pause size={12} /> Pause
                      </button>
                    )}
                    <button onClick={() => triggerAgent(active)}
                      className="flex items-center gap-1.5 bg-indigo-600 text-white text-xs font-bold px-3 py-2 rounded-xl hover:bg-indigo-700 transition-colors">
                      <Zap size={12} /> Trigger Now
                    </button>
                  </div>
                </div>

                {agentState?.status === "error" && (
                  <div className="flex items-center gap-2 text-xs font-semibold text-red-700 bg-red-50 border border-red-200 rounded-xl px-3 py-2 mb-4">
                    <AlertTriangle size={13} /> Agent encountered an error — check logs
                  </div>
                )}

                <div className="grid grid-cols-4 gap-3">
                  {[
                    { label: "Queue", val: agentState?.queue ?? 0 },
                    { label: "Done Today", val: agentState?.completed_today ?? 0 },
                    { label: "Failed", val: agentState?.failed_today ?? 0, red: (agentState?.failed_today ?? 0) > 0 },
                    { label: "Orchestrator", val: agentState?.orchestrator_running ? "ON" : "OFF", green: agentState?.orchestrator_running },
                  ].map(({ label, val, red, green }) => (
                    <div key={label} className="text-center bg-gray-50 rounded-xl py-3 border border-gray-100">
                      <div className={`text-xl font-black ${red ? "text-red-500" : green ? "text-emerald-600" : "text-gray-900"}`}>{val}</div>
                      <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wide mt-0.5">{label}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* All agents overview */}
              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <div className="flex items-center justify-between px-5 py-3.5 border-b border-gray-100">
                  <h3 className="text-sm font-bold text-gray-900">All Agents Overview</h3>
                  <span className="text-xs font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">{agents.length} agents</span>
                </div>
                <table className="w-full">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-100">
                      {["Agent", "Status", "Queue", "Completed", "Failed", "Actions"].map(h => (
                        <th key={h} className="text-left text-[10px] font-bold text-gray-400 uppercase tracking-wider px-4 py-2.5">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {agents.map(a => {
                      const m = AGENT_META[a.agent_type];
                      if (!m) return null;
                      const AIcon = m.icon;
                      return (
                        <tr key={a.agent_type} className={`border-b border-gray-50 hover:bg-gray-50 transition-colors cursor-pointer ${active === a.agent_type ? "bg-indigo-50/50" : ""}`}
                          onClick={() => setActive(a.agent_type)}>
                          <td className="px-4 py-2.5">
                            <div className="flex items-center gap-2">
                              <AIcon size={13} style={{ color: m.color }} />
                              <span className="text-xs font-semibold text-gray-800">{m.name}</span>
                            </div>
                          </td>
                          <td className="px-4 py-2.5">
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                              a.status === "active" ? "bg-emerald-100 text-emerald-700" :
                              a.status === "paused" ? "bg-amber-100 text-amber-700" :
                              "bg-red-100 text-red-600"
                            }`}>{a.status}</span>
                          </td>
                          <td className="px-4 py-2.5 text-xs font-bold text-gray-600">{a.queue}</td>
                          <td className="px-4 py-2.5 text-xs text-emerald-600 font-bold">{a.completed_today}</td>
                          <td className="px-4 py-2.5 text-xs text-red-500 font-bold">{a.failed_today}</td>
                          <td className="px-4 py-2.5">
                            <div className="flex items-center gap-1">
                              {a.status === "paused" ? (
                                <button onClick={(e) => { e.stopPropagation(); resumeAgent(a.agent_type); }}
                                  className="text-[10px] font-bold text-emerald-600 hover:text-emerald-700 px-1.5 py-0.5 rounded bg-emerald-50 hover:bg-emerald-100">
                                  Resume
                                </button>
                              ) : (
                                <button onClick={(e) => { e.stopPropagation(); pauseAgent(a.agent_type); }}
                                  className="text-[10px] font-bold text-amber-600 hover:text-amber-700 px-1.5 py-0.5 rounded bg-amber-50 hover:bg-amber-100">
                                  Pause
                                </button>
                              )}
                              <button onClick={(e) => { e.stopPropagation(); triggerAgent(a.agent_type); }}
                                className="text-[10px] font-bold text-indigo-600 hover:text-indigo-700 px-1.5 py-0.5 rounded bg-indigo-50 hover:bg-indigo-100">
                                Trigger
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                {loading && (
                  <div className="p-8 text-center text-xs text-gray-400 font-medium">Loading agents...</div>
                )}
              </div>
            </div>

            {/* Config panel */}
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-bold text-gray-900 mb-4">
                Configuration — {meta.name}
              </h3>
              {configLoading ? (
                <div className="text-xs text-gray-400 text-center py-8">Loading config...</div>
              ) : config ? (
                <div className="space-y-4">
                  {[
                    { label: "Max Call Attempts", key: "max_cold_call_attempts" as const, type: "number" },
                    { label: "Cooldown (minutes)", key: "cooldown_minutes" as const, type: "number" },
                    { label: "Follow-up Delay (hours)", key: "follow_up_delay_hours" as const, type: "number" },
                    { label: "Calling Hours Start", key: "calling_hours_start" as const, type: "number" },
                    { label: "Calling Hours End", key: "calling_hours_end" as const, type: "number" },
                    { label: "Confidence Threshold", key: "auto_reply_confidence_threshold" as const, type: "number" },
                    { label: "Max Task Retries", key: "max_task_retries" as const, type: "number" },
                  ].map(({ label, key, type }) => (
                    <div key={key}>
                      <label className="text-[11px] font-bold text-gray-500 uppercase tracking-wide block mb-1">{label}</label>
                      <input
                        value={config[key]}
                        onChange={(e) => setConfig({ ...config, [key]: key === "auto_reply_confidence_threshold" ? parseFloat(e.target.value) || 0 : parseInt(e.target.value) || 0 })}
                        type={type}
                        step={key === "auto_reply_confidence_threshold" ? "0.05" : "1"}
                        className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm font-medium text-gray-800 outline-none focus:border-indigo-400 focus:bg-white transition-all"
                      />
                    </div>
                  ))}
                  <button onClick={saveConfig}
                    className="w-full bg-indigo-600 text-white text-xs font-bold py-2.5 rounded-xl hover:bg-indigo-700 transition-colors mt-2">
                    Save Configuration
                  </button>
                </div>
              ) : (
                <div className="text-xs text-gray-400 text-center py-8">Failed to load config</div>
              )}
            </div>
          </div>
        </main>
      </div>

      {toast && (
        <div className={`fixed bottom-6 right-6 text-white text-xs font-bold px-4 py-3 rounded-xl shadow-lg z-50 ${toast.startsWith("Failed") ? "bg-red-600" : "bg-indigo-600"}`}>
          {toast}
        </div>
      )}
    </div>
  );
}
