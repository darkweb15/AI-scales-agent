"use client";
import { useState } from "react";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import { Phone, Mail, Calendar, MessageSquare, Inbox, PhoneIncoming, Pause, Play, AlertTriangle, CheckCircle2, Settings, X } from "lucide-react";

const AGENTS = [
  { id:"cold_calling",    name:"Cold Calling",    icon: Phone,         status:"active", queue:24,  done:87,  failed:2,  success:94, color:"#4F8EF7", grad:"from-accent-blue to-accent-purple" },
  { id:"follow_up",       name:"Follow-up",        icon: Mail,          status:"active", queue:41,  done:132, failed:1,  success:88, color:"#34D399", grad:"from-accent-green to-[#06B6D4]" },
  { id:"demo_scheduling", name:"Demo Scheduling",  icon: Calendar,      status:"active", queue:8,   done:19,  failed:0,  success:97, color:"#4F8EF7", grad:"from-[#0284C7] to-accent-blue" },
  { id:"auto_mail",       name:"Auto Mail",         icon: MessageSquare, status:"paused", queue:0,   done:204, failed:0,  success:99, color:"#FBBF24", grad:"from-accent-amber to-[#F97316]" },
  { id:"auto_reply",      name:"Auto Reply",        icon: Inbox,         status:"active", queue:12,  done:56,  failed:3,  success:91, color:"#A78BFA", grad:"from-accent-purple to-[#7C3AED]" },
  { id:"call_answering",  name:"Call Answering",    icon: PhoneIncoming, status:"error",  queue:3,   done:31,  failed:5,  success:76, color:"#F87171", grad:"from-accent-red to-[#E11D48]" },
];

const TASKS = [
  { lead:"Sarah Johnson",  company:"TechCorp",   action:"call",           priority:1, attempts:1, scheduled:"10:30 AM" },
  { lead:"Mike Chen",      company:"DataSoft",   action:"follow_up",      priority:2, attempts:2, scheduled:"10:45 AM" },
  { lead:"Priya Sharma",   company:"Acme Corp",  action:"schedule_demo",  priority:1, attempts:1, scheduled:"11:00 AM" },
  { lead:"James Wilson",   company:"CloudBase",  action:"call",           priority:3, attempts:0, scheduled:"11:15 AM" },
];

export default function AgentsPage() {
  const [collapsed, setCollapsed] = useState(false);
  const [active, setActive] = useState("cold_calling");
  const [states, setStates] = useState<Record<string,string>>(Object.fromEntries(AGENTS.map(a=>[a.id,a.status])));

  const agent = AGENTS.find(a => a.id === active)!;
  const Icon = agent.icon;

  return (
    <div className="flex h-screen overflow-hidden bg-bg-base">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-5">
          <div className="mb-5">
            <h2 className="text-lg font-black text-text-primary">Agent Control Panel</h2>
            <p className="text-xs text-text-muted mt-0.5">Monitor and control all AI agents</p>
          </div>

          {/* Agent tabs */}
          <div className="flex items-center gap-2 mb-5 flex-wrap">
            {AGENTS.map(a => {
              const AIcon = a.icon;
              const st = states[a.id];
              return (
                <button key={a.id} onClick={() => setActive(a.id)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold transition-all border ${
                    active === a.id ? "bg-accent-blue text-white border-accent-blue shadow-lg shadow-accent-blue/20" : "bg-bg-elevated text-text-secondary border-border hover:border-accent-blue/30"
                  }`}>
                  <AIcon size={13} />
                  {a.name}
                  <span className={`w-1.5 h-1.5 rounded-full ${st==="active"?"bg-accent-green":st==="paused"?"bg-accent-amber":"bg-accent-red"}`} />
                </button>
              );
            })}
          </div>

          <div className="grid grid-cols-3 gap-5">
            {/* Agent detail */}
            <div className="col-span-2 space-y-4">
              {/* Header card */}
              <div className="card p-5">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${agent.grad} flex items-center justify-center shadow-md`}>
                      <Icon size={22} className="text-white" />
                    </div>
                    <div>
                      <h3 className="text-base font-black text-text-primary">{agent.name} Agent</h3>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className={`w-2 h-2 rounded-full ${states[active]==="active"?"bg-accent-green pulse-dot":states[active]==="paused"?"bg-accent-amber":"bg-accent-red"}`} />
                        <span className={`text-xs font-bold ${states[active]==="active"?"text-accent-green":states[active]==="paused"?"text-accent-amber":"text-accent-red"}`}>
                          {states[active] === "active" ? "Running" : states[active] === "paused" ? "Paused" : "Error"}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {states[active] === "paused" ? (
                      <button onClick={() => setStates(s=>({...s,[active]:"active"}))}
                        className="flex items-center gap-1.5 bg-accent-green text-white text-xs font-bold px-3 py-2 rounded-xl hover:brightness-110 transition-colors">
                        <Play size={12} /> Resume
                      </button>
                    ) : (
                      <button onClick={() => setStates(s=>({...s,[active]:"paused"}))}
                        className="flex items-center gap-1.5 bg-bg-elevated text-text-secondary text-xs font-bold px-3 py-2 rounded-xl hover:bg-bg-subtle transition-colors border border-border">
                        <Pause size={12} /> Pause
                      </button>
                    )}
                    <button className="flex items-center gap-1.5 bg-bg-elevated text-text-secondary text-xs font-bold px-3 py-2 rounded-xl hover:bg-bg-subtle transition-colors border border-border">
                      <Settings size={12} /> Config
                    </button>
                  </div>
                </div>

                {states[active] === "error" && (
                  <div className="flex items-center gap-2 text-xs font-semibold text-accent-red bg-accent-red-dim border border-accent-red/20 rounded-xl px-3 py-2 mb-4">
                    <AlertTriangle size={13} /> Telephony API timeout — retrying in 30s
                  </div>
                )}

                <div className="grid grid-cols-4 gap-3">
                  {[
                    { label:"Queue",    val: agent.queue },
                    { label:"Done Today", val: agent.done },
                    { label:"Failed",   val: agent.failed, red: agent.failed > 0 },
                    { label:"Success",  val: `${agent.success}%`, green: agent.success >= 90 },
                  ].map(({ label, val, red, green }) => (
                    <div key={label} className="text-center bg-bg-elevated rounded-xl py-3 border border-border">
                      <div className={`text-xl font-black ${red?"text-accent-red":green?"text-accent-green":"text-text-primary"}`}>{val}</div>
                      <div className="text-[10px] font-bold text-text-muted uppercase tracking-wide mt-0.5">{label}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Task queue */}
              <div className="card overflow-hidden">
                <div className="flex items-center justify-between px-5 py-3.5 border-b border-border">
                  <h3 className="text-sm font-bold text-text-primary">Live Task Queue</h3>
                  <span className="text-xs font-bold text-accent-blue bg-accent-blue-dim px-2 py-0.5 rounded-full">{TASKS.length} tasks</span>
                </div>
                <table className="w-full">
                  <thead>
                    <tr className="bg-bg-elevated border-b border-border">
                      {["Lead","Company","Action","Priority","Attempts","Scheduled",""].map(h => (
                        <th key={h} className="text-left text-[10px] font-bold text-text-muted uppercase tracking-wider px-4 py-2.5">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {TASKS.map((t, i) => (
                      <tr key={i} className="border-b border-border/50 hover:bg-bg-elevated/50 transition-colors">
                        <td className="px-4 py-2.5 text-xs font-semibold text-text-primary">{t.lead}</td>
                        <td className="px-4 py-2.5 text-xs text-text-secondary">{t.company}</td>
                        <td className="px-4 py-2.5">
                          <span className="text-[10px] font-bold bg-accent-blue-dim text-accent-blue px-2 py-0.5 rounded-full">{t.action}</span>
                        </td>
                        <td className="px-4 py-2.5 text-xs font-bold text-text-secondary">P{t.priority}</td>
                        <td className="px-4 py-2.5 text-xs text-text-secondary">{t.attempts}</td>
                        <td className="px-4 py-2.5 text-xs text-text-secondary">{t.scheduled}</td>
                        <td className="px-4 py-2.5">
                          <button className="text-[10px] font-bold text-accent-red hover:text-accent-red/80 transition-colors">Cancel</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Config panel */}
            <div className="card p-5">
              <h3 className="text-sm font-bold text-text-primary mb-4">Configuration</h3>
              <div className="space-y-4">
                {[
                  { label:"Max Call Attempts", val:"3", type:"number" },
                  { label:"Cooldown (minutes)", val:"60", type:"number" },
                  { label:"Follow-up Delay (hours)", val:"24", type:"number" },
                  { label:"Calling Hours Start", val:"9", type:"number" },
                  { label:"Calling Hours End", val:"17", type:"number" },
                  { label:"Confidence Threshold", val:"0.75", type:"number" },
                  { label:"Max Task Retries", val:"3", type:"number" },
                ].map(({ label, val, type }) => (
                  <div key={label}>
                    <label className="text-[11px] font-bold text-text-muted uppercase tracking-wide block mb-1">{label}</label>
                    <input defaultValue={val} type={type}
                      className="w-full bg-bg-elevated border border-border rounded-lg px-3 py-2 text-sm font-medium text-text-primary outline-none focus:border-accent-blue/50 transition-all" />
                  </div>
                ))}
                <button className="w-full bg-accent-blue text-white text-xs font-bold py-2.5 rounded-xl hover:brightness-110 transition-colors mt-2 shadow-lg shadow-accent-blue/20">
                  Save Configuration
                </button>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
