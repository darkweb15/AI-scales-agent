"use client";
import { Phone, Mail, Calendar, MessageSquare, Inbox, PhoneIncoming, Pause, Play, AlertTriangle, Zap, CheckCircle2, Clock } from "lucide-react";

const agents = [
  { name: "Cold Calling",   icon: Phone,        status: "active", queue: 24,  done: 87,  success: 94, grad: "from-[#6366F1] to-[#8B5CF6]", bar: "#6366F1", lastAction: "Called Sarah J. — interested",  time: "2m ago" },
  { name: "Follow-up",      icon: Mail,         status: "active", queue: 41,  done: 132, success: 88, grad: "from-[#059669] to-[#10B981]", bar: "#059669", lastAction: "Email sent to DataSoft Inc",      time: "45s ago" },
  { name: "Demo Sched.",    icon: Calendar,     status: "active", queue: 8,   done: 19,  success: 97, grad: "from-[#0284C7] to-[#38BDF8]", bar: "#0284C7", lastAction: "Booked demo — Acme Corp",         time: "5m ago" },
  { name: "Auto Mail",      icon: MessageSquare,status: "paused", queue: 0,   done: 204, success: 99, grad: "from-[#D97706] to-[#F59E0B]", bar: "#D97706", lastAction: "Paused by operator",              time: "1h ago" },
  { name: "Auto Reply",     icon: Inbox,        status: "active", queue: 12,  done: 56,  success: 91, grad: "from-[#7C3AED] to-[#A78BFA]", bar: "#7C3AED", lastAction: "Replied to Mike Chen",            time: "1m ago" },
  { name: "Call Answering", icon: PhoneIncoming,status: "error",  queue: 3,   done: 31,  success: 76, grad: "from-[#DC2626] to-[#F87171]", bar: "#DC2626", lastAction: "Telephony API timeout",           time: "Error" },
];

export default function AgentStatusCards() {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-base font-black text-[#0A0F1E] tracking-tight flex items-center gap-2">
            <Zap size={16} className="text-indigo-500" />
            AI Agents
          </h2>
          <p className="text-xs text-[#94A3B8] font-semibold mt-0.5">Autonomous agents working in real-time</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-full">
            <span className="agent-active-dot scale-75" /> 5 Active
          </span>
          <span className="flex items-center gap-1.5 text-xs font-bold text-amber-700 bg-amber-50 border border-amber-200 px-3 py-1.5 rounded-full">
            <Clock size={10} /> 1 Paused
          </span>
          <span className="flex items-center gap-1.5 text-xs font-bold text-red-700 bg-red-50 border border-red-200 px-3 py-1.5 rounded-full">
            <AlertTriangle size={10} /> 1 Error
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 xl:grid-cols-3 gap-4">
        {agents.map(({ name, icon: Icon, status, queue, done, success, grad, bar, lastAction, time }) => (
          <div
            key={name}
            className={`bg-white rounded-2xl border glow-card card-shine overflow-hidden ${
              status === "error" ? "border-red-200" : status === "paused" ? "border-amber-100" : "border-[#E8EEFF]"
            }`}
            style={{ boxShadow: status === "error" ? "0 2px 12px rgba(220,38,38,0.08)" : "0 2px 12px rgba(99,102,241,0.06)" }}
          >
            {/* Top bar */}
            <div className="h-0.5" style={{ background: `linear-gradient(90deg, ${bar}, ${bar}88)` }} />

            <div className="p-4">
              {/* Header */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2.5">
                  <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${grad} flex items-center justify-center shadow-md`}>
                    <Icon size={18} className="text-white" />
                  </div>
                  <div>
                    <div className="text-sm font-extrabold text-[#0A0F1E]">{name}</div>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      {status === "active" && <span className="agent-active-dot" style={{ width: 7, height: 7 }} />}
                      {status === "paused" && <span className="w-1.5 h-1.5 rounded-full bg-amber-400 inline-block" />}
                      {status === "error" && <span className="w-1.5 h-1.5 rounded-full bg-red-500 inline-block" />}
                      <span className={`text-[11px] font-bold ${status === "active" ? "text-emerald-600" : status === "paused" ? "text-amber-600" : "text-red-600"}`}>
                        {status === "active" ? "Running" : status === "paused" ? "Paused" : "Error"}
                      </span>
                    </div>
                  </div>
                </div>
                {status === "active" && <CheckCircle2 size={16} className="text-emerald-400" />}
                {status === "error" && <AlertTriangle size={16} className="text-red-500" />}
              </div>

              {/* Error message */}
              {status === "error" && (
                <div className="mb-3 flex items-center gap-2 text-xs font-bold text-red-700 bg-red-50 border border-red-200 rounded-xl px-3 py-2">
                  <AlertTriangle size={11} /> Telephony API timeout — retrying
                </div>
              )}

              {/* Stats row */}
              <div className="grid grid-cols-3 gap-2 mb-3">
                {[
                  { label: "Queue", val: String(queue) },
                  { label: "Done", val: String(done) },
                  { label: "Rate", val: `${success}%`, highlight: success >= 90 ? "text-emerald-600" : "text-amber-600" },
                ].map(({ label, val, highlight }) => (
                  <div key={label} className="text-center bg-[#F6F8FF] rounded-xl py-2 border border-[#EEF2FF]">
                    <div className={`text-base font-black ${highlight || "text-[#0A0F1E]"}`}>{val}</div>
                    <div className="text-[9px] font-bold text-[#94A3B8] uppercase tracking-wide">{label}</div>
                  </div>
                ))}
              </div>

              {/* Progress */}
              <div className="mb-3">
                <div className="h-2 bg-[#F1F5F9] rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-1000"
                    style={{ width: `${success}%`, background: `linear-gradient(90deg, ${bar}, ${bar}99)` }}
                  />
                </div>
              </div>

              {/* Last action */}
              <div className="flex items-center gap-1.5 mb-3 bg-[#F6F8FF] rounded-lg px-2.5 py-1.5">
                <div className="w-1 h-1 rounded-full shrink-0" style={{ backgroundColor: bar }} />
                <span className="text-[10px] font-semibold text-[#64748B] truncate flex-1">{lastAction}</span>
                <span className="text-[9px] font-bold text-[#94A3B8] shrink-0">{time}</span>
              </div>

              {/* Button */}
              <button className={`w-full flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-extrabold transition-all ${
                status === "paused"
                  ? "bg-gradient-to-r from-emerald-500 to-emerald-600 text-white shadow-md shadow-emerald-200 hover:shadow-lg"
                  : status === "error"
                  ? "bg-gradient-to-r from-red-500 to-red-600 text-white shadow-md shadow-red-200"
                  : "bg-[#F6F8FF] text-[#64748B] hover:bg-[#EEF2FF] hover:text-indigo-600 border border-[#E8EEFF]"
              }`}>
                {status === "paused" ? <><Play size={11} /> Resume Agent</>
                 : status === "error" ? <><AlertTriangle size={11} /> View Error</>
                 : <><Pause size={11} /> Pause Agent</>}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
