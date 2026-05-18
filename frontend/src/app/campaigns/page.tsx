"use client";
import { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import { Mail, Phone, Send, Eye, TrendingUp, Play, CheckCircle, X } from "lucide-react";

export default function CampaignsPage() {
  const [collapsed, setCollapsed] = useState(false);
  const [stats, setStats] = useState<any>(null);
  const [sending, setSending] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [emailCount, setEmailCount] = useState(10);
  const [toast, setToast] = useState("");

  useEffect(() => {
    fetch("http://localhost:8001/api/campaigns/stats")
      .then(r => r.json())
      .then(setStats)
      .catch(() => {});
  }, []);

  const sendEmails = async () => {
    setSending(true);
    setResults(null);
    try {
      const res = await fetch("http://localhost:8001/api/campaigns/send-intro-emails", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ limit: emailCount }),
      });
      const data = await res.json();
      setResults(data);
      setToast(data.message);
      setTimeout(() => setToast(""), 5000);
      // Refresh stats
      fetch("http://localhost:8001/api/campaigns/stats").then(r => r.json()).then(setStats);
    } catch {
      setToast("❌ Failed to send emails");
    }
    setSending(false);
  };

  return (
    <div className="flex h-screen overflow-hidden bg-bg-base">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-5">
          <div className="mb-5">
            <h2 className="text-lg font-black text-text-primary">Smart Campaign Sequence</h2>
            <p className="text-xs text-text-muted mt-0.5">Email first → Call openers → Book demos</p>
          </div>

          {/* Flow diagram */}
          <div className="card p-5 mb-5">
            <h3 className="text-sm font-bold text-text-primary mb-4">How It Works</h3>
            <div className="flex items-center gap-3 flex-wrap">
              {[
                { icon: Mail,        label: "Send Email",      sub: "Pebble intro to all leads",    color: "#4F8EF7" },
                { icon: Eye,         label: "Track Opens",     sub: "Who opened in 24-48h?",        color: "#FBBF24" },
                { icon: Phone,       label: "Call Openers",    sub: "Warm leads — 3x conversion",   color: "#34D399" },
                { icon: Phone,       label: "Call Rest",       sub: "Cold outreach to non-openers", color: "#A78BFA" },
                { icon: CheckCircle, label: "Book Demo",       sub: "Auto-schedule via Bland AI",   color: "#34D399" },
              ].map(({ icon: Icon, label, sub, color }, i) => (
                <div key={label} className="flex items-center gap-2">
                  <div className="bg-bg-elevated rounded-xl p-3 text-center min-w-28 border border-border">
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center mx-auto mb-1.5" style={{ backgroundColor: color + "15" }}>
                      <Icon size={16} style={{ color }} />
                    </div>
                    <div className="text-xs font-bold text-text-primary">{label}</div>
                    <div className="text-[10px] text-text-muted mt-0.5">{sub}</div>
                  </div>
                  {i < 4 && <div className="text-text-muted font-bold text-lg">→</div>}
                </div>
              ))}
            </div>
          </div>

          {/* Stats */}
          {stats && (
            <div className="grid grid-cols-5 gap-4 mb-5">
              {[
                { label: "Total Leads",    val: stats.total_leads,       color: "#4F8EF7" },
                { label: "Emailable",      val: stats.emailable_leads,   color: "#34D399" },
                { label: "Emails Sent",    val: stats.total_emails_sent, color: "#FBBF24" },
                { label: "Interested",     val: stats.interested,        color: "#A78BFA" },
                { label: "Demos Booked",   val: stats.demos_scheduled,   color: "#34D399" },
              ].map(({ label, val, color }) => (
                <div key={label} className="card p-4 text-center">
                  <div className="text-2xl font-black text-text-primary">{val}</div>
                  <div className="text-[11px] font-bold text-text-muted uppercase tracking-wide mt-0.5">{label}</div>
                  <div className="mt-2 h-1 bg-bg-elevated rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: "100%", backgroundColor: color }} />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Send emails */}
          <div className="card p-5 mb-5">
            <h3 className="text-sm font-bold text-text-primary mb-4">Step 1 — Send Pebble Intro Emails</h3>
            <div className="flex items-center gap-4 mb-4">
              <div>
                <label className="text-[11px] font-bold text-text-muted uppercase tracking-wide block mb-1">How many emails to send?</label>
                <select value={emailCount} onChange={e => setEmailCount(Number(e.target.value))}
                  className="bg-bg-elevated border border-border rounded-xl px-3 py-2 text-sm font-medium text-text-primary outline-none">
                  <option value={5}>5 emails (test)</option>
                  <option value={10}>10 emails</option>
                  <option value={25}>25 emails</option>
                  <option value={50}>50 emails</option>
                  <option value={100}>100 emails</option>
                </select>
              </div>
              <div className="flex-1">
                <label className="text-[11px] font-bold text-text-muted uppercase tracking-wide block mb-1">Email preview</label>
                <a href="http://localhost:8001/api/campaigns/email-preview" target="_blank"
                  className="text-xs font-bold text-accent-blue hover:underline">
                  Preview Pebble email template
                </a>
              </div>
            </div>
            <button onClick={sendEmails} disabled={sending}
              className="flex items-center gap-2 bg-accent-blue text-white text-sm font-bold px-6 py-3 rounded-xl hover:brightness-110 transition-colors disabled:opacity-50 shadow-lg shadow-accent-blue/20">
              <Send size={15} />
              {sending ? `Sending ${emailCount} emails...` : `Send ${emailCount} Pebble Intro Emails`}
            </button>
          </div>

          {/* Results */}
          {results && (
            <div className="card overflow-hidden">
              <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                <h3 className="text-sm font-bold text-text-primary">Send Results</h3>
                <div className="flex items-center gap-3">
                  <span className="text-xs font-bold text-accent-green bg-accent-green-dim px-2 py-0.5 rounded-full">{results.sent} sent</span>
                  {results.failed > 0 && <span className="text-xs font-bold text-accent-red bg-accent-red-dim px-2 py-0.5 rounded-full">{results.failed} failed</span>}
                  {results.skipped > 0 && <span className="text-xs font-bold text-text-muted bg-bg-subtle px-2 py-0.5 rounded-full">{results.skipped} skipped</span>}
                </div>
              </div>
              <div className="divide-y divide-border/50 max-h-64 overflow-y-auto">
                {results.results?.map((r: any, i: number) => (
                  <div key={i} className="flex items-center justify-between px-5 py-2.5">
                    <div>
                      <div className="text-xs font-semibold text-text-primary">{r.lead} — {r.company}</div>
                      <div className="text-[10px] text-text-muted">{r.email}</div>
                    </div>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${r.success ? "bg-accent-green-dim text-accent-green" : "bg-accent-red-dim text-accent-red"}`}>
                      {r.success ? "Sent" : `Failed: ${r.error || r.reason}`}
                    </span>
                  </div>
                ))}
              </div>
              <div className="px-5 py-3 bg-accent-blue-dim border-t border-accent-blue/20">
                <p className="text-xs font-semibold text-accent-blue">
                  Next: Wait 24-48 hours, then call the leads who opened the email first!
                </p>
              </div>
            </div>
          )}
        </main>
      </div>

      {toast && (
        <div className="fixed bottom-6 right-6 bg-accent-blue text-white text-xs font-bold px-4 py-3 rounded-xl shadow-lg z-50 max-w-sm">
          {toast}
        </div>
      )}
    </div>
  );
}
