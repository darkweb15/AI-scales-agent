"use client";
import { Search, Filter, Download, MoreHorizontal, Phone, Mail } from "lucide-react";

const leads = [
  { name: "Sarah Johnson", company: "TechCorp Ltd", email: "sarah@techcorp.com", status: "interested", agent: "Cold Calling", calls: 2, emails: 1, last: "2m ago" },
  { name: "Mike Chen", company: "DataSoft Inc", email: "mike@datasoft.io", status: "contacted", agent: "Follow-up", calls: 3, emails: 2, last: "15m ago" },
  { name: "Priya Sharma", company: "Acme Corp", email: "priya@acme.com", status: "demo_scheduled", agent: "Demo Scheduling", calls: 1, emails: 3, last: "1h ago" },
  { name: "James Wilson", company: "CloudBase", email: "james@cloudbase.io", status: "new", agent: "Cold Calling", calls: 0, emails: 0, last: "2h ago" },
  { name: "Emily Davis", company: "NexGen AI", email: "emily@nexgen.ai", status: "converted", agent: "Auto Mail", calls: 4, emails: 6, last: "1d ago" },
  { name: "Ravi Kumar", company: "FinTech Pro", email: "ravi@fintechpro.in", status: "follow_up_scheduled", agent: "Follow-up", calls: 2, emails: 2, last: "3h ago" },
];

const statusBadge: Record<string, string> = {
  new: "bg-slate-100 text-slate-600",
  contacted: "bg-sky-100 text-sky-700",
  interested: "bg-emerald-100 text-emerald-700",
  follow_up_scheduled: "bg-amber-100 text-amber-700",
  demo_scheduled: "bg-indigo-100 text-indigo-700",
  converted: "bg-green-100 text-green-700",
  not_interested: "bg-red-100 text-red-600",
};

const statusLabel: Record<string, string> = {
  new: "New",
  contacted: "Contacted",
  interested: "Interested",
  follow_up_scheduled: "Follow-up",
  demo_scheduled: "Demo Set",
  converted: "Converted",
  not_interested: "Not Interested",
};

export default function LeadsTable() {
  return (
    <div className="bg-white rounded-2xl border-2 border-[#E2E8F0] shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b-2 border-[#F1F5F9]">
        <div>
          <h2 className="text-base font-extrabold text-[#0F172A]">Recent Leads</h2>
          <p className="text-xs text-[#64748B] font-medium mt-0.5">1,240 total · showing 6</p>
        </div>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-2 bg-[#F1F5F9] border-2 border-[#E2E8F0] rounded-xl px-3 py-2 text-xs font-bold text-[#64748B] hover:bg-[#E2E8F0] transition-colors">
            <Filter size={13} /> Filter
          </button>
          <button className="flex items-center gap-2 bg-[#F1F5F9] border-2 border-[#E2E8F0] rounded-xl px-3 py-2 text-xs font-bold text-[#64748B] hover:bg-[#E2E8F0] transition-colors">
            <Download size={13} /> Export
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-[#F8FAFC] border-b-2 border-[#F1F5F9]">
              {["Lead", "Company", "Status", "Agent", "Calls", "Emails", "Last Contact", ""].map(h => (
                <th key={h} className="text-left text-[11px] font-extrabold text-[#94A3B8] uppercase tracking-wider px-5 py-3">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {leads.map((lead, i) => (
              <tr key={i} className="border-b border-[#F1F5F9] hover:bg-[#F8FAFC] transition-colors cursor-pointer">
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#4F46E5] to-[#7C3AED] flex items-center justify-center text-white text-xs font-bold shrink-0">
                      {lead.name.charAt(0)}
                    </div>
                    <div>
                      <div className="text-sm font-bold text-[#0F172A]">{lead.name}</div>
                      <div className="text-[11px] text-[#94A3B8] font-medium">{lead.email}</div>
                    </div>
                  </div>
                </td>
                <td className="px-5 py-3.5 text-sm font-semibold text-[#475569]">{lead.company}</td>
                <td className="px-5 py-3.5">
                  <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full ${statusBadge[lead.status]}`}>
                    {statusLabel[lead.status]}
                  </span>
                </td>
                <td className="px-5 py-3.5 text-xs font-semibold text-[#64748B]">{lead.agent}</td>
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-1 text-xs font-bold text-[#475569]">
                    <Phone size={11} className="text-indigo-400" /> {lead.calls}
                  </div>
                </td>
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-1 text-xs font-bold text-[#475569]">
                    <Mail size={11} className="text-emerald-400" /> {lead.emails}
                  </div>
                </td>
                <td className="px-5 py-3.5 text-xs font-semibold text-[#94A3B8]">{lead.last}</td>
                <td className="px-5 py-3.5">
                  <button className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-[#E2E8F0] text-[#94A3B8] transition-colors">
                    <MoreHorizontal size={15} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-6 py-3 bg-[#F8FAFC] border-t-2 border-[#F1F5F9]">
        <span className="text-xs font-semibold text-[#94A3B8]">Showing 6 of 1,240 leads</span>
        <button className="text-xs font-bold text-indigo-600 hover:text-indigo-700 transition-colors">View all leads →</button>
      </div>
    </div>
  );
}
