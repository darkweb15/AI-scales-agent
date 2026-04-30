"use client";
import { Trophy, ArrowUpRight } from "lucide-react";

const agents = [
  { rank: 1, name: "Arjun Patel",  av: "AP", color: "#6366F1", score: 95 },
  { rank: 2, name: "Priya Sharma", av: "PS", color: "#8B5CF6", score: 88 },
  { rank: 3, name: "Rahul Verma",  av: "RV", color: "#06B6D4", score: 87 },
  { rank: 4, name: "Sneha Reddy",  av: "SR", color: "#10B981", score: 84 },
  { rank: 5, name: "Karan Singh",  av: "KS", color: "#F59E0B", score: 76 },
];

const rankMedal = ["🥇", "🥈", "🥉", "4", "5"];

export default function TopAgents() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <Trophy size={14} className="text-amber-500" />
          <div>
            <h2 className="text-sm font-bold text-gray-900">Top Performing Agents</h2>
            <p className="text-[11px] text-gray-400 mt-0.5">This Week</p>
          </div>
        </div>
        <button className="flex items-center gap-1 text-xs font-semibold text-indigo-600">
          Full Leaderboard <ArrowUpRight size={11} />
        </button>
      </div>
      <div className="p-3 space-y-1.5">
        {agents.map(({ rank, name, av, color, score }) => (
          <div key={rank} className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer">
            <span className="text-sm w-5 text-center shrink-0">{rankMedal[rank - 1]}</span>
            <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0"
              style={{ background: `linear-gradient(135deg, ${color}, ${color}88)` }}>
              {av}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-semibold text-gray-800 truncate">{name}</div>
              <div className="mt-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
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
