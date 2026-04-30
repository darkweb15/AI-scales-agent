"use client";
import { Search, Bell, Plus, ChevronDown, Sparkles } from "lucide-react";

export default function Topbar() {
  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6 shrink-0">
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-base font-bold text-gray-900">Dashboard</h1>
          <span className="flex items-center gap-1 bg-emerald-50 border border-emerald-200 rounded-full px-2 py-0.5 text-[10px] font-bold text-emerald-700">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 pulse-dot inline-block" />
            5 Agents Active
          </span>
          <span className="bg-amber-50 border border-amber-200 rounded-full px-2 py-0.5 text-[10px] font-bold text-amber-700">
            1 Paused
          </span>
        </div>
        <p className="text-[11px] text-gray-400 mt-0.5">Fri, Apr 24 2026 · 847 actions today</p>
      </div>

      <div className="flex items-center gap-2">
        <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 w-48 focus-within:border-indigo-400 focus-within:bg-white transition-all">
          <Search size={13} className="text-gray-400 shrink-0" />
          <input placeholder="Search anything..." className="bg-transparent text-xs text-gray-800 placeholder-gray-400 outline-none w-full" />
          <kbd className="text-[9px] font-bold text-gray-400 bg-gray-200 px-1.5 py-0.5 rounded shrink-0">⌘K</kbd>
        </div>

        <button className="flex items-center gap-1.5 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-xs font-semibold text-gray-600 hover:border-indigo-300 transition-all">
          Last 7 days <ChevronDown size={11} />
        </button>

        <button className="flex items-center gap-1.5 bg-violet-50 border border-violet-200 rounded-xl px-3 py-2 text-xs font-semibold text-violet-700 hover:bg-violet-100 transition-all">
          <Sparkles size={12} className="text-violet-500" /> AI Insights
        </button>

        <button className="flex items-center gap-1.5 bg-indigo-600 rounded-xl px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-indigo-700 transition-all">
          <Plus size={13} /> Add Lead
        </button>

        <button className="relative w-9 h-9 flex items-center justify-center rounded-xl bg-gray-50 border border-gray-200 text-gray-500 hover:border-indigo-300 transition-all">
          <Bell size={15} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border border-white" />
        </button>
      </div>
    </header>
  );
}
