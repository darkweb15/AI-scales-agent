"use client";
import { Trophy, ArrowUpRight } from "lucide-react";

const agents = [
  { rank: 1, name: "Arjun Patel",  av: "AP", color: "#4F8EF7", score: 95 },
  { rank: 2, name: "Priya Sharma", av: "PS", color: "#A78BFA", score: 88 },
  { rank: 3, name: "Rahul Verma",  av: "RV", color: "#34D399", score: 87 },
  { rank: 4, name: "Sneha Reddy",  av: "SR", color: "#FBBF24", score: 84 },
  { rank: 5, name: "Karan Singh",  av: "KS", color: "#F87171", score: 76 },
];

const rankMedal = ["#1", "#2", "#3", "#4", "#5"];

export default function TopAgents() {
  return (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-border">
        <div className="flex items-center gap-2">
          <Trophy size={14} className="text-accent-amber" />
          <div>
            <h2 className="text-sm font-bold text-text-primary">Top Performing Agents</h2>
            <p className="text-[11px] text-text-muted mt-0.5">This Week</p>
          </div>
        </div>
        <button className="flex items-center gap-1 text-xs font-semibold text-accent-blue">
          Full Leaderboard <ArrowUpRight size={11} />
        </button>
      </div>
      <div className="p-3 space-y-1.5">
        {agents.map(({ rank, name, av, color, score }) => (
          <div key={rank} className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-bg-elevated transition-colors cursor-pointer">
            <span className="text-xs font-bold w-5 text-center shrink-0 text-text-muted">{rankMedal[rank - 1]}</span>
            <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0"
              style={{ background: `linear-gradient(135deg, ${color}, ${color}88)` }}>
              {av}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-semibold text-text-primary truncate">{name}</div>
              <div className="mt-1 h-1.5 bg-bg-elevated rounded-full overflow-hidden">
                <div className="h-full rounded-full transition-all" style={{ width: `${score}%`, backgroundColor: color }} />
              </div>
            </div>
            <span className="text-xs font-bold shrink-0" style={{ color }}>{score}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
