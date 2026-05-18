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
                className="text-[11px] font-medium text-indigo-700 bg-white border border-indigo-200 px-3 py-1 rounded-full hover:bg-indigo-50 transition-colors shadow-sm">
                {s}
              </button>
            ))}
          </div>
        )}
        <div className={`flex items-center gap-3 bg-white border-2 rounded-2xl px-4 py-2.5 shadow-lg transition-all ${focused ? "border-indigo-400 shadow-indigo-100" : "border-gray-200"}`}>
          <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shrink-0">
            <Sparkles size={12} className="text-white" />
          </div>
          <input
            value={q}
            onChange={e => setQ(e.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => setTimeout(() => setFocused(false), 150)}
            placeholder="Ask AI Assistant anything about your sales..."
            className="flex-1 text-sm text-gray-800 placeholder-gray-400 outline-none bg-transparent"
          />
          <div className="flex items-center gap-1.5 shrink-0">
            <button className="w-7 h-7 rounded-lg bg-gray-100 flex items-center justify-center text-gray-400 hover:bg-gray-200 transition-colors">
              <Mic size={13} />
            </button>
            <button className={`w-7 h-7 rounded-lg flex items-center justify-center transition-all ${q ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-300"}`}>
              <Send size={12} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
