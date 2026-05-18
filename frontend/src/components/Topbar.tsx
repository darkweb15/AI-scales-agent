"use client";
import { Search, Bell, Plus, ChevronDown, Sparkles } from "lucide-react";

export default function Topbar() {
  return (
    <header className="h-14 bg-bg-surface border-b border-border flex items-center justify-between px-6 shrink-0">
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-base font-bold text-text-primary">Dashboard</h1>
          <span className="flex items-center gap-1 bg-accent-green-dim border border-accent-green/20 rounded-full px-2 py-0.5 text-[10px] font-bold text-accent-green">
            <span className="w-1.5 h-1.5 rounded-full bg-accent-green pulse-dot inline-block" />
            5 Agents Active
          </span>
          <span className="bg-accent-amber-dim border border-accent-amber/20 rounded-full px-2 py-0.5 text-[10px] font-bold text-accent-amber">
            1 Paused
          </span>
        </div>
        <p className="text-[11px] text-text-muted mt-0.5">Fri, Apr 24 2026 &middot; 847 actions today</p>
      </div>

      <div className="flex items-center gap-2">
        <div className="flex items-center gap-2 bg-bg-elevated border border-border rounded-xl px-3 py-2 w-48 focus-within:border-accent-blue/50 transition-all">
          <Search size={13} className="text-text-muted shrink-0" />
          <input placeholder="Search anything..." className="bg-transparent text-xs text-text-primary placeholder-text-muted outline-none w-full" />
          <kbd className="text-[9px] font-bold text-text-muted bg-bg-subtle px-1.5 py-0.5 rounded shrink-0">/</kbd>
        </div>

        <button className="flex items-center gap-1.5 bg-bg-elevated border border-border rounded-xl px-3 py-2 text-xs font-semibold text-text-secondary hover:border-accent-blue/30 transition-all">
          Last 7 days <ChevronDown size={11} />
        </button>

        <button className="flex items-center gap-1.5 bg-accent-purple/10 border border-accent-purple/20 rounded-xl px-3 py-2 text-xs font-semibold text-accent-purple hover:bg-accent-purple/15 transition-all">
          <Sparkles size={12} /> AI Insights
        </button>

        <button className="flex items-center gap-1.5 bg-accent-blue rounded-xl px-4 py-2 text-xs font-bold text-white shadow-lg shadow-accent-blue/20 hover:brightness-110 transition-all">
          <Plus size={13} /> Add Lead
        </button>

        <button className="relative w-9 h-9 flex items-center justify-center rounded-xl bg-bg-elevated border border-border text-text-secondary hover:border-accent-blue/30 transition-all">
          <Bell size={15} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-accent-red rounded-full border-2 border-bg-surface" />
        </button>
      </div>
    </header>
  );
}
