"use client";
import { useState } from "react";
import { Sparkles, Send, Mic } from "lucide-react";

const suggestions = [
  "Which leads should I call today?",
  "Show me this week's conversion rate",
  "Who are my top performing agents?",
];

export default function AIAssistantBar() {
  const [q, setQ] = useState("");
  const [focused, setFocused] = useState(false);

  return (
    <div className="absolute bottom-0 left-0 right-0 px-5 pb-3 pointer-events-none">
      <div className="pointer-events-auto max-w-2xl mx-auto">
        {focused && (
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            {suggestions.map(s => (
              <button key={s} onClick={() => setQ(s)}
                className="text-[11px] font-medium text-accent-blue bg-bg-elevated border border-accent-blue/20 px-3 py-1 rounded-full hover:bg-accent-blue/10 transition-colors">
                {s}
              </button>
            ))}
          </div>
        )}
        <div className={`flex items-center gap-3 bg-bg-surface border-2 rounded-2xl px-4 py-2.5 shadow-2xl transition-all ${focused ? "border-accent-blue/50 shadow-accent-blue/10" : "border-border"}`}>
          <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center shrink-0">
            <Sparkles size={12} className="text-white" />
          </div>
          <input
            value={q}
            onChange={e => setQ(e.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => setTimeout(() => setFocused(false), 150)}
            placeholder="Ask AI Assistant anything about your sales..."
            className="flex-1 text-sm text-text-primary placeholder-text-muted outline-none bg-transparent"
          />
          <div className="flex items-center gap-1.5 shrink-0">
            <button className="w-7 h-7 rounded-lg bg-bg-elevated flex items-center justify-center text-text-muted hover:bg-bg-subtle hover:text-text-secondary transition-colors">
              <Mic size={13} />
            </button>
            <button className={`w-7 h-7 rounded-lg flex items-center justify-center transition-all ${q ? "bg-accent-blue text-white" : "bg-bg-elevated text-text-muted"}`}>
              <Send size={12} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
