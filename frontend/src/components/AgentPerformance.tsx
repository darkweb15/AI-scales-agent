"use client";
import { ArrowUpRight } from "lucide-react";

function MiniSpark({ data, color }: { data: number[]; color: string }) {
  const max = Math.max(...data), min = Math.min(...data), r = max - min || 1;
  const W = 72, H = 28;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * W},${H - ((v - min) / r) * (H - 4) - 2}`);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-18 h-7" style={{ width: 72, height: 28 }} preserveAspectRatio="none">
      <defs>
        <linearGradient id={`m${color.replace("#","")}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.25" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`M 0,${H} L ${pts.join(" L ")} L ${W},${H} Z`} fill={`url(#m${color.replace("#","")})`} />
      <path d={`M ${pts.join(" L ")}`} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const agents = [
  { name: "Arjun Patel",  av: "AP", color: "#4F8EF7", calls: 156, demos: 18, emails: 42, bonus: 12, success: 92, data: [60,72,65,80,70,85,78,90,82,92] },
  { name: "Priya Sharma", av: "PS", color: "#A78BFA", calls: 142, demos: 16, emails: 38, bonus: 10, success: 88, data: [55,68,60,75,65,80,72,85,78,88] },
  { name: "Rahul Verma",  av: "RV", color: "#34D399", calls: 128, demos: 14, emails: 35, bonus: 8,  success: 87, data: [50,62,55,70,60,75,68,80,74,87] },
  { name: "Sneha Reddy",  av: "SR", color: "#FBBF24", calls: 58,  demos: 11, emails: 28, bonus: 6,  success: 84, data: [40,52,45,60,50,65,58,70,64,84] },
  { name: "Karan Singh",  av: "KS", color: "#F87171", calls: 44,  demos: 8,  emails: 20, bonus: 4,  success: 76, data: [30,42,35,50,40,55,48,60,54,76] },
];

export default function AgentPerformance() {
  return (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-border">
        <div>
          <h2 className="text-sm font-bold text-text-primary">Agent Performance</h2>
          <p className="text-[11px] text-text-muted mt-0.5">Real-time overview</p>
        </div>
        <button className="flex items-center gap-1 text-xs font-semibold text-accent-blue hover:text-accent-blue/80">
          View All Agents <ArrowUpRight size={12} />
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-bg-elevated border-b border-border">
              {["Agent", "Calls", "Demos", "Emails", "Bonus", "Success", "Trend"].map(h => (
                <th key={h} className="text-left text-[10px] font-bold text-text-muted uppercase tracking-wider px-4 py-2.5 first:pl-5">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {agents.map((a) => (
              <tr key={a.name} className="border-b border-border/50 hover:bg-bg-elevated/50 transition-colors">
                <td className="px-5 py-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0"
                      style={{ background: `linear-gradient(135deg, ${a.color}, ${a.color}88)` }}>
                      {a.av}
                    </div>
                    <div>
                      <div className="text-xs font-semibold text-text-primary">{a.name}</div>
                      <div className="flex items-center gap-1 mt-0.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-accent-green inline-block pulse-dot" />
                        <span className="text-[10px] text-text-muted">Active</span>
                      </div>
                    </div>
                  </div>
                </td>
                {[a.calls, a.demos, a.emails, a.bonus].map((val, i) => (
                  <td key={i} className="px-4 py-3">
                    <div className="text-sm font-bold text-text-primary">{val}</div>
                  </td>
                ))}
                <td className="px-4 py-3">
                  <div className="text-sm font-bold" style={{ color: a.color }}>{a.success}%</div>
                  <div className="mt-1 h-1 w-14 bg-bg-elevated rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${a.success}%`, backgroundColor: a.color }} />
                  </div>
                </td>
                <td className="px-4 py-3">
                  <MiniSpark data={a.data} color={a.color} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
