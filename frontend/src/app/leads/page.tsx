"use client";
import { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import AddLeadModal from "@/components/AddLeadModal";
import { Search, MoreHorizontal, Phone, Mail, Plus, X, PhoneCall, RefreshCw } from "lucide-react";

const STATUSES = ["new","contacted","interested","follow_up_scheduled","demo_scheduled","demo_completed","converted","not_interested","unsubscribed","do_not_contact"];

const STATUS_BADGE: Record<string, string> = {
  new: "bg-slate-100 text-slate-600",
  contacted: "bg-sky-100 text-sky-700",
  interested: "bg-emerald-100 text-emerald-700",
  follow_up_scheduled: "bg-amber-100 text-amber-700",
  demo_scheduled: "bg-indigo-100 text-indigo-700",
  demo_completed: "bg-violet-100 text-violet-700",
  converted: "bg-green-100 text-green-700",
  not_interested: "bg-red-100 text-red-600",
  unsubscribed: "bg-gray-100 text-gray-500",
  do_not_contact: "bg-red-200 text-red-800",
};

export default function LeadsPage() {
  const [collapsed, setCollapsed] = useState(false);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [calling, setCalling] = useState<string | null>(null);
  const [callResult, setCallResult] = useState("");
  const [voiceProvider, setVoiceProvider] = useState("vapi");
  const [leads, setLeads] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);

  const fetchLeads = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (search) params.set("search", search);
      if (statusFilter) params.set("status", statusFilter);
      const res = await fetch(`http://localhost:8001/api/leads?${params}`);
      const data = await res.json();
      setLeads(Array.isArray(data) ? data : []);
    } catch {
      setLeads([]);
    }
    setLoading(false);
  };

  useEffect(() => { fetchLeads(); }, [search, statusFilter]);

  const testCall = async (phone: string, name: string, leadId: string = "") => {
    if (!phone) { setCallResult("❌ No phone number for this lead"); return; }
    setCalling(phone);
    setCallResult("");
    try {
      const res = await fetch("http://localhost:8001/api/test-call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ to_number: phone, lead_id: leadId, provider: voiceProvider }),
      });
      const data = await res.json();
      setCallResult(data.success
        ? `🎙️ ${data.message}`
        : `❌ Call failed: ${data.error}`);
    } catch {
      setCallResult("❌ Backend not reachable");
    }
    setCalling(null);
  };

  const toggleSelect = (id: string) =>
    setSelected(s => s.includes(id) ? s.filter(x => x !== id) : [...s, id]);

  return (
    <div className="flex h-screen overflow-hidden bg-[#F8F9FC]">
      {showAddModal && <AddLeadModal onClose={() => setShowAddModal(false)} onAdded={fetchLeads} />}
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-5">          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-lg font-black text-gray-900">Leads</h2>
              <p className="text-xs text-gray-400 mt-0.5">{leads.length} leads in Supabase</p>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={fetchLeads} className="flex items-center gap-1.5 bg-white border border-gray-200 rounded-xl px-3 py-2 text-xs font-bold text-gray-600 hover:border-indigo-300 transition-all">
                <RefreshCw size={12} /> Refresh
              </button>
              <button onClick={() => setShowAddModal(true)} className="flex items-center gap-1.5 bg-indigo-600 rounded-xl px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-indigo-700 transition-all">
                <Plus size={13} /> Add Lead
              </button>
            </div>
          </div>

          <div className="flex items-center gap-3 mb-4">
            <div className="flex items-center gap-2 bg-white border border-gray-200 rounded-xl px-3 py-2 w-64">
              <Search size={13} className="text-gray-400 shrink-0" />
              <input value={search} onChange={e => setSearch(e.target.value)}
                placeholder="Search leads..." className="bg-transparent text-xs text-gray-800 placeholder-gray-400 outline-none w-full" />
              {search && <button onClick={() => setSearch("")}><X size={12} className="text-gray-400" /></button>}
            </div>
            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
              className="bg-white border border-gray-200 rounded-xl px-3 py-2 text-xs font-medium text-gray-600 outline-none cursor-pointer">
              <option value="">All Statuses</option>
              {STATUSES.map(s => <option key={s} value={s}>{s.replace(/_/g," ")}</option>)}
            </select>
            {/* Voice Provider Selector */}
            <div className="flex items-center gap-1.5 bg-white border border-gray-200 rounded-xl px-3 py-2">
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wide">Voice:</span>
              <select value={voiceProvider} onChange={e => setVoiceProvider(e.target.value)}
                className="bg-transparent text-xs font-semibold text-indigo-600 outline-none cursor-pointer">
                <option value="vapi">🎙️ Vapi (ElevenLabs Rachel)</option>
                <option value="bland">🇮🇳 Bland AI (Maya — Indian)</option>
                <option value="elevenlabs">✨ ElevenLabs + Twilio</option>
                <option value="twilio">📞 Twilio (Polly.Aditi)</option>
              </select>
            </div>
            {selected.length > 0 && (
              <div className="flex items-center gap-2 ml-auto">
                <span className="text-xs font-semibold text-gray-600">{selected.length} selected</span>
                <button className="text-xs font-bold text-red-600 bg-red-50 border border-red-200 px-3 py-1.5 rounded-lg">Mark DNC</button>
                <button className="text-xs font-bold text-indigo-600 bg-indigo-50 border border-indigo-200 px-3 py-1.5 rounded-lg">Export CSV</button>
              </div>
            )}
          </div>

          {callResult && (
            <div className={`flex items-center gap-2 px-4 py-3 rounded-xl text-xs font-bold mb-3 ${callResult.startsWith("✅") ? "bg-emerald-50 border border-emerald-200 text-emerald-700" : "bg-red-50 border border-red-200 text-red-700"}`}>
              {callResult}
              <button onClick={() => setCallResult("")} className="ml-auto"><X size={12} /></button>
            </div>
          )}

          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            {loading ? (
              <div className="flex items-center justify-center py-16 text-sm text-gray-400">Loading from Supabase...</div>
            ) : leads.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16">
                <div className="text-4xl mb-3">👤</div>
                <p className="text-sm font-semibold text-gray-500">No leads found</p>
              </div>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-100">
                    <th className="w-10 px-4 py-3">
                      <input type="checkbox" className="rounded" onChange={e => setSelected(e.target.checked ? leads.map((l:any)=>l.id) : [])} />
                    </th>
                    {["Lead","Company","Status","Agent","Calls","Emails","Last Contact","Actions"].map(h => (
                      <th key={h} className="text-left text-[10px] font-bold text-gray-400 uppercase tracking-wider px-4 py-3">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {leads.map((lead: any) => (
                    <tr key={lead.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3">
                        <input type="checkbox" className="rounded" checked={selected.includes(lead.id)}
                          onChange={() => toggleSelect(lead.id)} />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2.5">
                          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white text-xs font-bold shrink-0">
                            {lead.first_name?.charAt(0) || "?"}
                          </div>
                          <div>
                            <div className="text-xs font-semibold text-gray-800">{lead.first_name} {lead.last_name}</div>
                            <div className="text-[10px] text-gray-400">{lead.email}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-600">{lead.company || "—"}</td>
                      <td className="px-4 py-3">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${STATUS_BADGE[lead.status] || "bg-gray-100 text-gray-500"}`}>
                          {(lead.status || "").replace(/_/g," ")}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">{lead.assigned_agent || "—"}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1 text-xs text-gray-600">
                          <Phone size={10} className="text-indigo-400" /> {lead.call_attempts}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1 text-xs text-gray-600">
                          <Mail size={10} className="text-emerald-400" /> {lead.email_attempts}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-[10px] text-gray-400">
                        {lead.last_contacted_at ? new Date(lead.last_contacted_at).toLocaleDateString() : "Never"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          {lead.phone && (
                            <button onClick={() => testCall(lead.phone, `${lead.first_name} ${lead.last_name}`, lead.id)}
                              disabled={calling === lead.phone}
                              className="flex items-center gap-1 text-[10px] font-bold text-indigo-600 bg-indigo-50 border border-indigo-200 px-2 py-1 rounded-lg hover:bg-indigo-100 disabled:opacity-50">
                              <PhoneCall size={10} />
                              {calling === lead.phone ? "Calling..." : "Call"}
                            </button>
                          )}
                          <button className="w-6 h-6 flex items-center justify-center rounded-lg hover:bg-gray-200 text-gray-400">
                            <MoreHorizontal size={13} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <div className="flex items-center justify-between px-5 py-3 bg-gray-50 border-t border-gray-100">
              <span className="text-xs text-gray-400">{leads.length} leads from Supabase</span>
              <button onClick={fetchLeads} className="text-xs font-bold text-indigo-600 hover:text-indigo-700">Refresh →</button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
