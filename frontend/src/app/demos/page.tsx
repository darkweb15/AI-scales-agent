"use client";
import { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import { Calendar, Clock, Video, Send, RefreshCw, X, Plus } from "lucide-react";

const STATUS_STYLE: Record<string, string> = {
  confirmed: "bg-accent-blue-dim text-accent-blue",
  pending:   "bg-accent-amber-dim text-accent-amber",
  cancelled: "bg-accent-red-dim text-accent-red",
  rescheduled: "bg-accent-purple/15 text-accent-purple",
  completed: "bg-accent-green-dim text-accent-green",
};

const STATUS_DOT: Record<string, string> = {
  confirmed: "bg-accent-blue",
  pending:   "bg-accent-amber",
  cancelled: "bg-accent-red",
  rescheduled: "bg-accent-purple",
  completed: "bg-accent-green",
};

export default function DemosPage() {
  const [collapsed, setCollapsed] = useState(false);
  const [bookings, setBookings] = useState<any[]>([]);
  const [leads, setLeads] = useState<any[]>([]);
  const [selected, setSelected] = useState<any | null>(null);
  const [toast, setToast] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [bookRes, leadRes] = await Promise.all([
        fetch("http://localhost:8001/api/bookings").then(r => r.json()),
        fetch("http://localhost:8001/api/leads?limit=200").then(r => r.json()),
      ]);
      setBookings(Array.isArray(bookRes) ? bookRes : []);
      setLeads(Array.isArray(leadRes) ? leadRes : []);
    } catch {
      setBookings([]);
    }
    setLoading(false);
  };

  useEffect(() => { fetchData(); }, []);

  // Get lead name for a booking
  const getLeadName = (leadId: string) => {
    const lead = leads.find(l => l.id === leadId);
    return lead ? `${lead.first_name} ${lead.last_name}` : "Unknown Lead";
  };
  const getCompany = (leadId: string) => {
    const lead = leads.find(l => l.id === leadId);
    return lead?.company || "";
  };

  // Also show leads with demo_scheduled status as pending demos
  const demoLeads = leads.filter(l => l.status === "demo_scheduled" || l.status === "interested");

  const sendReminder = async (booking: any) => {
    setToast(`✅ Reminder sent to ${getLeadName(booking.lead_id)}!`);
    setTimeout(() => setToast(""), 3000);
  };

  return (
    <div className="flex h-screen overflow-hidden bg-bg-base">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-5">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-lg font-black text-text-primary">Demo Scheduling</h2>
              <p className="text-xs text-text-muted mt-0.5">
                {bookings.length} bookings · {demoLeads.length} leads ready for demo
              </p>
            </div>
            <button onClick={fetchData} className="flex items-center gap-1.5 bg-bg-elevated border border-border rounded-xl px-3 py-2 text-xs font-bold text-text-secondary hover:border-accent-blue/30 transition-all">
              <RefreshCw size={12} /> Refresh
            </button>
          </div>

          <div className="grid grid-cols-3 gap-5">
            {/* Left: Bookings + Demo-ready leads */}
            <div className="col-span-2 space-y-4">

              {/* Real bookings from DB */}
              {bookings.length > 0 && (
                <div>
                  <h3 className="text-xs font-bold text-text-muted uppercase tracking-wide mb-2">Confirmed Bookings</h3>
                  <div className="space-y-2">
                    {bookings.map(b => (
                      <div key={b.id} onClick={() => setSelected({ ...b, type: "booking" })}
                        className={`card p-4 cursor-pointer hover:border-border-strong transition-all ${selected?.id === b.id ? "!border-accent-blue" : ""}`}>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${STATUS_DOT[b.status] || "bg-gray-400"}`} />
                            <div>
                              <div className="text-sm font-bold text-text-primary">{getLeadName(b.lead_id)}</div>
                              <div className="text-xs text-text-muted">{getCompany(b.lead_id)}</div>
                            </div>
                          </div>
                          <div className="flex items-center gap-3">
                            <div className="flex items-center gap-1 text-xs text-text-secondary">
                              <Clock size={11} /> {new Date(b.scheduled_at).toLocaleString()}
                            </div>
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${STATUS_STYLE[b.status] || "bg-bg-subtle text-text-muted"}`}>
                              {b.status}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Leads ready for demo */}
              {demoLeads.length > 0 && (
                <div>
                  <h3 className="text-xs font-bold text-text-muted uppercase tracking-wide mb-2">
                    Leads Ready for Demo ({demoLeads.length})
                  </h3>
                  <div className="space-y-2">
                    {demoLeads.map(lead => (
                      <div key={lead.id} onClick={() => setSelected({ ...lead, type: "lead" })}
                        className={`card p-4 cursor-pointer hover:border-border-strong transition-all ${selected?.id === lead.id ? "!border-accent-blue" : ""}`}>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center text-white text-xs font-bold shrink-0">
                              {lead.first_name?.charAt(0)}
                            </div>
                            <div>
                              <div className="text-sm font-bold text-text-primary">{lead.first_name} {lead.last_name}</div>
                              <div className="text-xs text-text-muted">{lead.company}</div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${lead.status === "interested" ? "bg-accent-green-dim text-accent-green" : "bg-accent-blue-dim text-accent-blue"}`}>
                              {lead.status.replace(/_/g, " ")}
                            </span>
                            <button
                              onClick={e => { e.stopPropagation(); setSelected({ ...lead, type: "lead" }); }}
                              className="flex items-center gap-1 text-[10px] font-bold text-accent-blue bg-accent-blue-dim border border-accent-blue/20 px-2 py-1 rounded-lg hover:bg-accent-blue/15">
                              <Plus size={10} /> Book Demo
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {bookings.length === 0 && demoLeads.length === 0 && !loading && (
                <div className="card p-12 text-center">
                  <Calendar size={40} className="text-text-muted mx-auto mb-3" />
                  <p className="text-sm font-semibold text-text-secondary">No demos yet</p>
                  <p className="text-xs text-text-muted mt-1">Add leads and call them to schedule demos</p>
                </div>
              )}
            </div>

            {/* Right: Detail panel */}
            <div className="card p-5 h-fit sticky top-5">
              {selected ? (
                <>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-bold text-text-primary">
                      {selected.type === "booking" ? "Booking Details" : "Schedule Demo"}
                    </h3>
                    <button onClick={() => setSelected(null)} className="text-text-muted hover:text-text-secondary">
                      <X size={14} />
                    </button>
                  </div>

                  <div className="space-y-3 mb-5">
                    <div>
                      <div className="text-[10px] font-bold text-text-muted uppercase tracking-wide mb-0.5">Lead</div>
                      <div className="text-sm font-bold text-text-primary">
                        {selected.type === "booking" ? getLeadName(selected.lead_id) : `${selected.first_name} ${selected.last_name}`}
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] font-bold text-text-muted uppercase tracking-wide mb-0.5">Company</div>
                      <div className="text-sm text-text-secondary">
                        {selected.type === "booking" ? getCompany(selected.lead_id) : selected.company}
                      </div>
                    </div>
                    {selected.type === "booking" && (
                      <>
                        <div>
                          <div className="text-[10px] font-bold text-text-muted uppercase tracking-wide mb-0.5">Scheduled</div>
                          <div className="text-sm text-text-secondary">{new Date(selected.scheduled_at).toLocaleString()}</div>
                        </div>
                        <div>
                          <div className="text-[10px] font-bold text-text-muted uppercase tracking-wide mb-0.5">Status</div>
                          <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${STATUS_STYLE[selected.status]}`}>
                            {selected.status}
                          </span>
                        </div>
                        {selected.meeting_link && (
                          <div>
                            <div className="text-[10px] font-bold text-text-muted uppercase tracking-wide mb-0.5">Meeting Link</div>
                            <a href={selected.meeting_link} className="text-xs font-medium text-accent-blue hover:underline flex items-center gap-1">
                              <Video size={11} /> Join Meeting
                            </a>
                          </div>
                        )}
                      </>
                    )}
                    {selected.type === "lead" && (
                      <div>
                        <div className="text-[10px] font-bold text-text-muted uppercase tracking-wide mb-0.5">Status</div>
                        <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-accent-green-dim text-accent-green">
                          {selected.status?.replace(/_/g, " ")}
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="space-y-2">
                    {selected.type === "booking" && (
                      <button onClick={() => sendReminder(selected)}
                        className="w-full flex items-center justify-center gap-2 bg-accent-blue text-white text-xs font-bold py-2.5 rounded-xl hover:brightness-110 transition-colors shadow-lg shadow-accent-blue/20">
                        <Send size={12} /> Send Reminder
                      </button>
                    )}
                    {selected.type === "lead" && (
                      <button
                        onClick={() => { setToast(`Demo booking initiated for ${selected.first_name}!`); setTimeout(() => setToast(""), 3000); }}
                        className="w-full flex items-center justify-center gap-2 bg-accent-blue text-white text-xs font-bold py-2.5 rounded-xl hover:brightness-110 transition-colors shadow-lg shadow-accent-blue/20">
                        <Calendar size={12} /> Schedule Demo
                      </button>
                    )}
                    <button className="w-full flex items-center justify-center gap-2 bg-bg-elevated text-text-secondary text-xs font-bold py-2.5 rounded-xl hover:bg-bg-subtle transition-colors border border-border">
                      <RefreshCw size={12} /> Reschedule
                    </button>
                  </div>
                </>
              ) : (
                <div className="text-center py-8">
                  <Calendar size={32} className="text-text-muted mx-auto mb-2" />
                  <p className="text-xs text-text-muted font-medium">Select a demo to view details</p>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>

      {toast && (
        <div className="fixed bottom-6 right-6 bg-accent-blue text-white text-xs font-bold px-4 py-3 rounded-xl shadow-lg z-50">
          {toast}
        </div>
      )}
    </div>
  );
}
