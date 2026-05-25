"use client";
import { useState } from "react";
import { Sparkles, Send, Loader2 } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

const defaultSuggestions = [
  "Which leads should I call today?",
  "Show me pipeline health",
  "Who are my top performing agents?",
];

export default function AIAssistantBar() {
  const [q, setQ] = useState("");
  const [focused, setFocused] = useState(false);
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>(defaultSuggestions);

  const askAI = async (question: string) => {
    if (!question.trim()) return;
    setLoading(true);
    setAnswer("");
    try {
      const res = await fetch(`${API}/api/ai/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const data = await res.json();
      setAnswer(data.answer || "No response received.");
      if (data.suggestions?.length) setSuggestions(data.suggestions);
    } catch {
      setAnswer("Failed to connect to AI. Please check the backend is running.");
    }
    setLoading(false);
  };

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    askAI(q);
  };

  return (
    <div className="absolute bottom-0 left-0 right-0 px-5 pb-3 pointer-events-none">
      <div className="pointer-events-auto max-w-2xl mx-auto">
        {answer && (
          <div className="mb-2 bg-indigo-50 border border-indigo-200 rounded-xl px-4 py-3 text-sm text-gray-800 shadow-sm">
            <div className="flex items-start gap-2">
              <Sparkles size={14} className="text-indigo-600 mt-0.5 shrink-0" />
              <p>{answer}</p>
            </div>
          </div>
        )}
        {focused && !loading && (
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            {suggestions.map(s => (
              <button key={s} onClick={() => { setQ(s); askAI(s); }}
                className="text-[11px] font-medium text-indigo-700 bg-white border border-indigo-200 px-3 py-1 rounded-full hover:bg-indigo-50 transition-colors shadow-sm">
                {s}
              </button>
            ))}
          </div>
        )}
        <form onSubmit={handleSubmit} className={`flex items-center gap-3 bg-white border-2 rounded-2xl px-4 py-2.5 shadow-lg transition-all ${focused ? "border-indigo-400 shadow-indigo-100" : "border-gray-200"}`}>
          <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shrink-0">
            <Sparkles size={12} className="text-white" />
          </div>
          <input
            value={q}
            onChange={e => setQ(e.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => setTimeout(() => setFocused(false), 200)}
            placeholder="Ask AI Assistant anything about your sales..."
            className="flex-1 text-sm text-gray-800 placeholder-gray-400 outline-none bg-transparent"
          />
          <div className="flex items-center gap-1.5 shrink-0">
            <button type="submit" disabled={!q.trim() || loading}
              className={`w-7 h-7 rounded-lg flex items-center justify-center transition-all ${q.trim() ? "bg-indigo-600 text-white hover:bg-indigo-700" : "bg-gray-100 text-gray-300"}`}>
              {loading ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
