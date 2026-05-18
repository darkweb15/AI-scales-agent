"use client";
import { Phone, Database, MapPin, Users } from "lucide-react";

function Spark({ data, color }: { data: number[]; color: string }) {
  const max = Math.max(...data), min = Math.min(...data), r = max - min || 1;
  const W = 120, H = 40;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * W},${H - ((v - min) / r) * (H - 6) - 3}`);
  const last = pts[pts.length - 1].split(",");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-full" preserveAspectRatio="none">
      <defs>
        <linearGradient id={`k${color.replace("#","")}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.25" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`M 0,${H} L ${pts.join(" L ")} L ${W},${H} Z`} fill={`url(#k${color.replace("#","")})`} />
      <path d={`M ${pts.join(" L ")}`} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={last[0]} cy={last[1]} r="3" fill={color} stroke="#111118" strokeWidth="1.5" />
    </svg>
  );
}

interface Props {
  stats?: any;
  totalLeads?: number;
  statusCounts?: Record<string, number>;
}

export default function KPICards({ stats, totalLeads = 0, statusCounts = {} }: Props) {
  const totalRecords  = stats?.total_records  ?? 0;
  const withPhone     = stats?.with_phone     ?? 0;
  const withAddress   = stats?.with_address   ?? 0;
  const phonePct      = stats?.phone_coverage_pct ?? 0;

  const cards = [
    {
      label: "Total Business Records",
      value: totalRecords.toLocaleString(),
      sub: "In your database",
      icon: Database,
      color: "#4F8EF7",
      data: [0, 5000, 10000, 15000, 18000, 21000, 23000, 25000, 26000, totalRecords || 26556],
    },
    {
      label: "Phone Numbers",
      value: withPhone.toLocaleString(),
      sub: `${phonePct}% coverage`,
      icon: Phone,
      color: "#34D399",
      data: [0, 4000, 8000, 12000, 15000, 18000, 20000, 22000, 23000, withPhone || 23889],
    },
    {
      label: "With Address",
      value: withAddress.toLocaleString(),
      sub: `${stats?.address_coverage_pct ?? 0}% location data`,
      icon: MapPin,
      color: "#FBBF24",
      data: [0, 4000, 8000, 12000, 16000, 19000, 21000, 23000, 24000, withAddress || 24672],
    },
    {
      label: "Leads in Pipeline",
      value: totalLeads.toLocaleString(),
      sub: `${statusCounts["interested"] || 0} interested · ${statusCounts["converted"] || 0} converted`,
      icon: Users,
      color: "#A78BFA",
      data: [0, 2, 4, 6, 8, 10, 12, 14, 16, totalLeads || 1],
    },
  ];

  return (
    <div className="grid grid-cols-4 gap-4">
      {cards.map(({ label, value, sub, icon: Icon, color, data }) => (
        <div key={label} className="card card-hover p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ backgroundColor: color + "15" }}>
              <Icon size={17} style={{ color }} />
            </div>
            <span className="text-[10px] font-bold text-accent-green bg-accent-green-dim px-2 py-0.5 rounded-full">LIVE</span>
          </div>
          <div className="text-2xl font-black text-text-primary tracking-tight">{value}</div>
          <div className="text-[11px] font-bold text-text-muted uppercase tracking-wide mt-0.5 mb-0.5">{label}</div>
          <div className="text-[10px] text-text-muted mb-3">{sub}</div>
          <div className="h-10">
            <Spark data={data} color={color} />
          </div>
        </div>
      ))}
    </div>
  );
}
