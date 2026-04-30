"use client";

const stages = [
  { label: "New Leads",       count: 1240, pct: 100, color: "#4F46E5", light: "#EEF2FF" },
  { label: "Contacted",       count: 834,  pct: 67,  color: "#7C3AED", light: "#F5F3FF" },
  { label: "Interested",      count: 412,  pct: 33,  color: "#0284C7", light: "#F0F9FF" },
  { label: "Follow-up",       count: 198,  pct: 16,  color: "#059669", light: "#ECFDF5" },
  { label: "Demo Scheduled",  count: 93,   pct: 7.5, color: "#D97706", light: "#FFFBEB" },
  { label: "Demo Completed",  count: 61,   pct: 5,   color: "#EA580C", light: "#FFF7ED" },
  { label: "Converted ✓",     count: 35,   pct: 2.8, color: "#16A34A", light: "#F0FDF4" },
];

export default function PipelineFunnel() {
  return (
    <div className="bg-white rounded-2xl border-2 border-[#E2E8F0] shadow-md overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b-2 border-[#F1F5F9]">
        <div>
          <h2 className="text-base font-black text-[#0F172A] tracking-tight">Sales Pipeline</h2>
          <p className="text-xs text-[#94A3B8] font-semibold mt-0.5">Lead progression funnel · This month</p>
        </div>
        <span className="text-xs font-extrabold text-indigo-700 bg-indigo-50 border-2 border-indigo-200 px-3 py-1.5 rounded-full">
          1,240 total leads
        </span>
      </div>

      {/* Funnel bars */}
      <div className="px-6 py-5 space-y-3">
        {stages.map(({ label, count, pct, color, light }) => (
          <div key={label} className="flex items-center gap-4">
            <div className="w-36 text-right shrink-0">
              <span className="text-xs font-bold text-[#475569]">{label}</span>
            </div>
            <div className="flex-1 h-9 bg-[#F8FAFC] rounded-xl overflow-hidden border border-[#F1F5F9]">
              <div
                className="h-full rounded-xl flex items-center px-3 gap-2 transition-all duration-700"
                style={{ width: `${pct}%`, backgroundColor: color }}
              >
                <span className="text-xs font-extrabold text-white drop-shadow-sm whitespace-nowrap">
                  {count.toLocaleString()}
                </span>
              </div>
            </div>
            <div className="w-10 text-right shrink-0">
              <span className="text-xs font-extrabold" style={{ color }}>{pct}%</span>
            </div>
          </div>
        ))}
      </div>

      {/* Summary footer */}
      <div className="grid grid-cols-3 gap-0 border-t-2 border-[#F1F5F9]">
        {[
          { label: "Conversion Rate", value: "2.8%", color: "text-emerald-600", bg: "bg-emerald-50" },
          { label: "Avg. Sales Cycle", value: "14 days", color: "text-indigo-600", bg: "bg-indigo-50" },
          { label: "Drop-off Rate", value: "97.2%", color: "text-red-500", bg: "bg-red-50" },
        ].map(({ label, value, color, bg }, i) => (
          <div key={label} className={`${bg} text-center py-4 px-3 ${i < 2 ? "border-r-2 border-[#F1F5F9]" : ""}`}>
            <div className={`text-xl font-black ${color}`}>{value}</div>
            <div className="text-[10px] font-bold text-[#94A3B8] uppercase tracking-wide mt-0.5">{label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
