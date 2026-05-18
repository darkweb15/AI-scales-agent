"use client";
import { useState } from "react";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import { Phone, Mail, Calendar, MessageSquare, Inbox, PhoneIncoming, Pause, Play, AlertTriangle, CheckCircle2, Settings, X } from "lucide-react";

const AGENTS = [
  { id:"cold_calling",    name:"Cold Calling",    icon: Phone,         status:"active", queue:24,  done:87,  failed:2,  success:94, color:"#6366F1", grad:"from-indigo-500 to-violet-600" },
  { id:"follow_up",       name:"Follow-up",        icon: Mail,          status:"active", queue:41,  done:132, failed:1,  success:88, color:"#10B981", grad:"from-emerald-500 to-teal-500" },
  { id:"demo_scheduling", name:"Demo Scheduling",  icon: Calendar,      status:"active", queue:8,   done:19,  failed:0,  success:97, color:"#0284C7", grad:"from-sky-500 to-cyan-500" },
  { id:"auto_mail",       name:"Auto Mail",         icon: MessageSquare, status:"paused", queue:0,   done:204, failed:0,  success:99, color:"#D97706", grad:"from-amber-400 to-orange-500" },
  { id:"auto_reply",      name:"Auto Reply",        icon: Inbox,         status:"active", queue:12,  done:56,  failed:3,  success:91, color:"#8B5CF6", grad:"from-violet-500 to-purple-600" },
  { id:"call_answering",  name:"Call Answering",    icon: PhoneIncoming, status:"error",  queue:3,   done:31,  failed:5,  success:76, color:"#DC2626", grad:"from-red-500 to-rose-600" },
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
    <div className="flex h-screen overflow-hidden bg-[#F8F9FC]">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-5">
          <div className="mb-5">
            <h2 className="text-lg font-black text-gray-900">Agent Control Panel</h2>
            <p className="text-xs text-gray-400 mt-0.5">Monitor and control all AI agents</p>
          </div>

          {/* Agent tabs */}
          <div className="flex items-center gap-2 mb-5 flex-wrap">
            {AGENTS.map(a => {
              const AIcon = a.icon;
              const st = states[a.id];
              return (
                <button key={a.id} onClick={() => setActive(a.id)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold transition-all border ${
                    active === a.id ? "bg-indigo-600 text-white border-indigo-600 shadow-sm" : "bg-white text-gray-600 border-gray-200 hover:border-indigo-300"
                  }`}>
                  <AIcon size={13} />
                  {a.name}
                  <span className={`w-1.5 h-1.5 rounded-full ${st==="active"?"bg-emerald-400":st==="paused"?"bg-amber-400":"bg-red-500"}`} />
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
                    <div className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${agent.grad} flex items-center justify-center shadow-md`}>
                      <Icon size={22} className="text-white" />
                    </div>
                    <div>
                      <h3 className="text-base font-black text-gray-900">{agent.name} Agent</h3>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className={`w-2 h-2 rounded-full ${states[active]==="active"?"bg-emerald-500 pulse-dot":states[active]==="paused"?"bg-amber-400":"bg-red-500"}`} />
                        <span className={`text-xs font-bold ${states[active]==="active"?"text-emerald-600":states[active]==="paused"?"text-amber-600":"text-red-600"}`}>
                          {states[active] === "active" ? "Running" : states[active] === "paused" ? "Paused" : "Error"}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {states[active] === "paused" ? (
                      <button onClick={() => setStates(s=>({...s,[active]:"active"}))}
                        className="flex items-center gap-1.5 bg-emerald-500 text-white text-xs font-bold px-3 py-2 rounded-xl hover:bg-emerald-600 transition-colors">
                        <Play size={12} /> Resume
                      </button>
                    ) : (
                      <button onClick={() => setStates(s=>({...s,[active]:"paused"}))}
                        className="flex items-center gap-1.5 bg-gray-100 text-gray-600 text-xs font-bold px-3 py-2 rounded-xl hover:bg-gray-200 transition-colors">
                        <Pause size={12} /> Pause
                      </button>
                    )}
                    <button className="flex items-center gap-1.5 bg-gray-100 text-gray-600 text-xs font-bold px-3 py-2 rounded-xl hover:bg-gray-200 transition-colors">
                      <Settings size={12} /> Config
                    </button>
                  </div>
                </div>

                {states[active] === "error" && (
                  <div className="flex items-center gap-2 text-xs font-semibold text-red-700 bg-red-50 border border-red-200 rounded-xl px-3 py-2 mb-4">
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
                    <div key={label} className="text-center bg-gray-50 rounded-xl py-3 border border-gray-100">
                      <div className={`text-xl font-black ${red?"text-red-500":green?"text-emerald-600":"text-gray-900"}`}>{val}</div>
                      <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wide mt-0.5">{label}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Task queue */}
              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <div className="flex items-center justify-between px-5 py-3.5 border-b border-gray-100">
                  <h3 className="text-sm font-bold text-gray-900">Live Task Queue</h3>
                  <span className="text-xs font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">{TASKS.length} tasks</span>
                </div>
                <table className="w-full">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-100">
                      {["Lead","Company","Action","Priority","Attempts","Scheduled",""].map(h => (
                        <th key={h} className="text-left text-[10px] font-bold text-gray-400 uppercase tracking-wider px-4 py-2.5">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {TASKS.map((t, i) => (
                      <tr key={i} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                        <td className="px-4 py-2.5 text-xs font-semibold text-gray-800">{t.lead}</td>
                        <td className="px-4 py-2.5 text-xs text-gray-500">{t.company}</td>
                        <td className="px-4 py-2.5">
                          <span className="text-[10px] font-bold bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full">{t.action}</span>
                        </td>
                        <td className="px-4 py-2.5 text-xs font-bold text-gray-600">P{t.priority}</td>
                        <td className="px-4 py-2.5 text-xs text-gray-500">{t.attempts}</td>
                        <td className="px-4 py-2.5 text-xs text-gray-500">{t.scheduled}</td>
                        <td className="px-4 py-2.5">
                          <button className="text-[10px] font-bold text-red-500 hover:text-red-700 transition-colors">Cancel</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Config panel */}
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-bold text-gray-900 mb-4">Configuration</h3>
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
                    <label className="text-[11px] font-bold text-gray-500 uppercase tracking-wide block mb-1">{label}</label>
                    <input defaultValue={val} type={type}
                      className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm font-medium text-gray-800 outline-none focus:border-indigo-400 focus:bg-white transition-all" />
                  </div>
                ))}
                <button className="w-full bg-indigo-600 text-white text-xs font-bold py-2.5 rounded-xl hover:bg-indigo-700 transition-colors mt-2">
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
