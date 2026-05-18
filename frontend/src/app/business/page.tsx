"use client";
import { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import {
  BarChart, Bar, PieChart, Pie, Cell, RadialBarChart, RadialBar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from "recharts";
import { Search, Phone, MapPin, Download, RefreshCw, X, Database, TrendingUp, Users, CheckCircle, AlertCircle } from "lucide-react";

const COLORS = ["#4F8EF7","#34D399","#FBBF24","#A78BFA","#F87171","#06B6D4","#EC4899","#84CC16","#F97316","#14B8A6","#A855F7","#EAB308","#3B82F6","#22C55E","#F43F5E"];

function StatCard({ label, value, sub, icon: Icon, color, pct }: any) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between mb-3">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: color + "15" }}>
          <Icon size={18} style={{ color }} />
        </div>
        {pct !== undefined && (
          <span className="text-xs font-bold px-2 py-0.5 rounded-full" style={{ backgroundColor: color + "15", color }}>
            {pct}%
          </span>
        )}
      </div>
      <div className="text-3xl font-black text-text-primary tracking-tight">{value}</div>
      <div className="text-[11px] font-bold text-text-muted uppercase tracking-wide mt-0.5">{label}</div>
      {sub && <div className="text-[10px] text-text-muted mt-0.5">{sub}</div>}
      {pct !== undefined && (
        <div className="mt-3 h-1.5 bg-bg-elevated rounded-full overflow-hidden">
          <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, backgroundColor: color }} />
        </div>
      )}
    </div>
  );
}

export default function BusinessDataPage() {
  const [collapsed, setCollapsed] = useState(false);
  const [data, setData] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [toast, setToast] = useState("");
  const [activeTab, setActiveTab] = useState<"analytics"|"browse">("analytics");

  const fetchData = async () => {
    setLoading(true);
    try {
      const [statsRes, dataRes] = await Promise.all([
        fetch("http://localhost:8001/api/business/stats").then(r => r.json()),
        fetch(`http://localhost:8001/api/business?limit=100${search ? `&search=${encodeURIComponent(search)}` : ""}`).then(r => r.json()),
      ]);
      setStats(statsRes);
      setData(Array.isArray(dataRes) ? dataRes : []);
    } catch { setData([]); }
    setLoading(false);
  };

  useEffect(() => { fetchData(); }, [search]);

  const importLeads = async (count: number) => {
    setImporting(true);
    try {
      const res = await fetch(`http://localhost:8001/api/business/import-as-leads?limit=${count}`, { method: "POST" });
      const result = await res.json();
      setToast(`✅ ${result.message}`);
      setTimeout(() => setToast(""), 4000);
    } catch { setToast("❌ Import failed"); }
    setImporting(false);
  };

  // Coverage donut data
  const coverageData = stats ? [
    { name: "With Phone", value: stats.with_phone, fill: "#34D399" },
    { name: "No Phone", value: stats.without_phone, fill: "#2A2A38" },
  ] : [];

  const addressData = stats ? [
    { name: "With Address", value: stats.with_address, fill: "#4F8EF7" },
    { name: "No Address", value: stats.total_records - stats.with_address, fill: "#2A2A38" },
  ] : [];

  return (
    <div className="flex h-screen overflow-hidden bg-bg-base">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-5">

          {/* Header */}
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-lg font-black text-text-primary flex items-center gap-2">
                <Database size={20} className="text-accent-blue" />
                Business Data Analytics
              </h2>
              <p className="text-xs text-text-muted mt-0.5">
                {stats ? `${stats.total_records?.toLocaleString()} total records` : "Loading..."}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex bg-bg-elevated rounded-xl p-1 border border-border">
                <button onClick={() => setActiveTab("analytics")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${activeTab === "analytics" ? "bg-accent-blue text-white shadow-lg shadow-accent-blue/20" : "text-text-secondary"}`}>
                  Analytics
                </button>
                <button onClick={() => setActiveTab("browse")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${activeTab === "browse" ? "bg-accent-blue text-white shadow-lg shadow-accent-blue/20" : "text-text-secondary"}`}>
                  Browse
                </button>
              </div>
              <button onClick={() => importLeads(50)} disabled={importing}
                className="flex items-center gap-1.5 bg-accent-blue text-white rounded-xl px-4 py-2 text-xs font-bold hover:brightness-110 transition-all disabled:opacity-50 shadow-lg shadow-accent-blue/20">
                <Download size={12} /> Import 50 as Leads
              </button>
            </div>
          </div>

          {toast && (
            <div className={`flex items-center gap-2 px-4 py-3 rounded-xl text-xs font-bold mb-4 ${toast.includes("failed") || toast.includes("Failed") ? "bg-accent-red-dim border border-accent-red/20 text-accent-red" : "bg-accent-green-dim border border-accent-green/20 text-accent-green"}`}>
              {toast}<button onClick={() => setToast("")} className="ml-auto"><X size={12} /></button>
            </div>
          )}

          {activeTab === "analytics" && stats && (
            <>
              {/* KPI Cards */}
              <div className="grid grid-cols-4 gap-4 mb-5">
                <StatCard label="Total Records" value={stats.total_records?.toLocaleString()} icon={Database} color="#4F8EF7" sub="In business_data table" />
                <StatCard label="With Phone" value={stats.with_phone?.toLocaleString()} icon={Phone} color="#34D399" pct={stats.phone_coverage_pct} sub="Ready to call" />
                <StatCard label="With Address" value={stats.with_address?.toLocaleString()} icon={MapPin} color="#FBBF24" pct={stats.address_coverage_pct} sub="Location available" />
                <StatCard label="No Phone" value={stats.without_phone?.toLocaleString()} icon={AlertCircle} color="#F87171" sub="Need phone research" />
              </div>

              {/* Charts row */}
              <div className="grid grid-cols-3 gap-5 mb-5">
                {/* Phone coverage donut */}
                <div className="card p-5">
                  <h3 className="text-sm font-bold text-text-primary mb-1">Phone Coverage</h3>
                  <p className="text-xs text-text-muted mb-4">{stats.phone_coverage_pct}% of records have phone</p>
                  <ResponsiveContainer width="100%" height={160}>
                    <PieChart>
                      <Pie data={coverageData} cx="50%" cy="50%" innerRadius={45} outerRadius={70} dataKey="value" startAngle={90} endAngle={-270}>
                        {coverageData.map((e, i) => <Cell key={i} fill={e.fill} />)}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="flex items-center justify-center gap-4 mt-2">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-accent-green" />
                      <span className="text-[11px] text-text-secondary">With Phone ({stats.with_phone?.toLocaleString()})</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-border" />
                      <span className="text-[11px] text-text-secondary">No Phone ({stats.without_phone?.toLocaleString()})</span>
                    </div>
                  </div>
                </div>

                {/* Address coverage donut */}
                <div className="card p-5">
                  <h3 className="text-sm font-bold text-text-primary mb-1">Address Coverage</h3>
                  <p className="text-xs text-text-muted mb-4">{stats.address_coverage_pct}% of records have address</p>
                  <ResponsiveContainer width="100%" height={160}>
                    <PieChart>
                      <Pie data={addressData} cx="50%" cy="50%" innerRadius={45} outerRadius={70} dataKey="value" startAngle={90} endAngle={-270}>
                        {addressData.map((e, i) => <Cell key={i} fill={e.fill} />)}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="flex items-center justify-center gap-4 mt-2">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-accent-blue" />
                      <span className="text-[11px] text-text-secondary">With Address</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-border" />
                      <span className="text-[11px] text-text-secondary">No Address</span>
                    </div>
                  </div>
                </div>

                {/* Summary stats */}
                <div className="card p-5">
                  <h3 className="text-sm font-bold text-text-primary mb-4">Data Quality Score</h3>
                  <div className="space-y-3">
                    {[
                      { label: "Phone Coverage", pct: stats.phone_coverage_pct, color: "#34D399" },
                      { label: "Address Coverage", pct: stats.address_coverage_pct, color: "#4F8EF7" },
                      { label: "Overall Quality", pct: Math.round((stats.phone_coverage_pct + stats.address_coverage_pct) / 2), color: "#A78BFA" },
                    ].map(({ label, pct, color }) => (
                      <div key={label}>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="font-semibold text-text-secondary">{label}</span>
                          <span className="font-bold" style={{ color }}>{pct}%</span>
                        </div>
                        <div className="h-2 bg-bg-elevated rounded-full overflow-hidden">
                          <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, backgroundColor: color }} />
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="mt-5 pt-4 border-t border-border">
                    <div className="text-xs font-bold text-text-secondary mb-2">Callable Records</div>
                    <div className="text-3xl font-black text-accent-green">{stats.with_phone?.toLocaleString()}</div>
                    <div className="text-[10px] text-text-muted mt-0.5">Ready for AI cold calling</div>
                    <button onClick={() => importLeads(100)} disabled={importing}
                      className="mt-3 w-full bg-accent-green text-white text-xs font-bold py-2 rounded-xl hover:brightness-110 transition-colors disabled:opacity-50">
                      Import 100 as Leads
                    </button>
                  </div>
                </div>
              </div>

              {/* Top States bar chart */}
              {stats.top_states?.length > 0 && (
                <div className="card p-5">
                  <h3 className="text-sm font-bold text-text-primary mb-1">Top States by Business Count</h3>
                  <p className="text-xs text-text-muted mb-4">Geographic distribution of your business database</p>
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={stats.top_states} margin={{ left: -10 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#2A2A38" />
                      <XAxis dataKey="state" tick={{ fontSize: 10, fill: "#55556A" }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fontSize: 10, fill: "#55556A" }} axisLine={false} tickLine={false} />
                      <Tooltip formatter={(v: any) => [v.toLocaleString(), "Businesses"]} />
                      <Bar dataKey="count" radius={[4,4,0,0]}>
                        {stats.top_states.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </>
          )}

          {activeTab === "browse" && (
            <>
              <div className="flex items-center gap-2 bg-bg-elevated border border-border rounded-xl px-3 py-2 w-80 mb-4">
                <Search size={13} className="text-text-muted shrink-0" />
                <input value={search} onChange={e => setSearch(e.target.value)}
                  placeholder="Search businesses..." className="bg-transparent text-xs text-text-primary placeholder-text-muted outline-none w-full" />
                {search && <button onClick={() => setSearch("")}><X size={12} className="text-text-muted" /></button>}
              </div>

              <div className="card overflow-hidden">
                {loading ? (
                  <div className="flex items-center justify-center py-16 text-sm text-text-muted">Loading records...</div>
                ) : (
                  <table className="w-full">
                    <thead>
                      <tr className="bg-bg-elevated border-b border-border">
                        {["ID", "Business Name", "Address", "Phone", ""].map(h => (
                          <th key={h} className="text-left text-[10px] font-bold text-text-muted uppercase tracking-wider px-4 py-3">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {data.map(row => (
                        <tr key={row.id} className="border-b border-border/50 hover:bg-bg-elevated/50 transition-colors">
                          <td className="px-4 py-2.5 text-[10px] text-text-muted font-mono">{row.id}</td>
                          <td className="px-4 py-2.5">
                            <div className="flex items-center gap-2">
                              <div className="w-7 h-7 rounded-lg bg-accent-blue-dim flex items-center justify-center shrink-0">
                                <span className="text-[10px] font-bold text-accent-blue">{row.name?.charAt(0) || "B"}</span>
                              </div>
                              <span className="text-xs font-semibold text-text-primary">{row.name}</span>
                            </div>
                          </td>
                          <td className="px-4 py-2.5">
                            <div className="flex items-center gap-1 text-[11px] text-text-secondary">
                              <MapPin size={10} className="text-text-muted shrink-0" />
                              <span className="truncate max-w-48">{row.address || "\u2014"}</span>
                            </div>
                          </td>
                          <td className="px-4 py-2.5">
                            {row.phone ? (
                              <div className="flex items-center gap-1 text-[11px] font-medium text-text-primary">
                                <Phone size={10} className="text-accent-green" />
                                {row.phone}
                              </div>
                            ) : <span className="text-[11px] text-text-muted">No phone</span>}
                          </td>
                          <td className="px-4 py-2.5">
                            <button onClick={async () => {
                              try {
                                await fetch("http://localhost:8001/api/leads", {
                                  method: "POST",
                                  headers: { "Content-Type": "application/json" },
                                  body: JSON.stringify({
                                    first_name: row.name?.split(" ")[0] || "Business",
                                    last_name: row.name?.split(" ").slice(1).join(" ") || "",
                                    email: `contact_${row.id}@business.com`,
                                    phone: row.phone,
                                    company: row.name,
                                    source: "business_data",
                                    notes: `Address: ${row.address}`,
                                  }),
                                });
                                setToast(`${row.name} added as lead!`);
                                setTimeout(() => setToast(""), 3000);
                              } catch { setToast("Import failed"); }
                            }}
                              className="text-[10px] font-bold text-accent-blue bg-accent-blue-dim border border-accent-blue/20 px-2 py-1 rounded-lg hover:bg-accent-blue/15 transition-colors">
                              + Add Lead
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                <div className="flex items-center justify-between px-5 py-3 bg-bg-elevated border-t border-border">
                  <span className="text-xs text-text-muted">Showing {data.length} of {stats?.total_records?.toLocaleString()} records</span>
                  <div className="flex items-center gap-2">
                    <button onClick={() => importLeads(20)} disabled={importing}
                      className="text-xs font-bold text-accent-blue hover:text-accent-blue/80">Import 20 as Leads</button>
                  </div>
                </div>
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
