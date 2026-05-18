"use client";
import { useState } from "react";
import { X, UserPlus } from "lucide-react";

interface Props {
  onClose: () => void;
  onAdded: () => void;
}

export default function AddLeadModal({ onClose, onAdded }: Props) {
  const [form, setForm] = useState({
    first_name: "", last_name: "", email: "", phone: "", company: "", source: "manual", notes: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async () => {
    if (!form.first_name || !form.email) { setError("Name and email are required"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await fetch("http://localhost:8001/api/leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error(await res.text());
      onAdded();
      onClose();
    } catch (e: any) {
      setError(e.message || "Failed to add lead");
    }
    setLoading(false);
  };

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl border border-gray-200 shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-indigo-600 flex items-center justify-center">
              <UserPlus size={15} className="text-white" />
            </div>
            <h2 className="text-sm font-black text-gray-900">Add New Lead</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
            <X size={18} />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: "First Name *", key: "first_name", placeholder: "John" },
              { label: "Last Name", key: "last_name", placeholder: "Doe" },
            ].map(({ label, key, placeholder }) => (
              <div key={key}>
                <label className="text-[11px] font-bold text-gray-500 uppercase tracking-wide block mb-1">{label}</label>
                <input value={(form as any)[key]} onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                  placeholder={placeholder}
                  className="w-full bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-sm text-gray-800 outline-none focus:border-indigo-400 focus:bg-white transition-all" />
              </div>
            ))}
          </div>

          {[
            { label: "Email *", key: "email", placeholder: "john@company.com", type: "email" },
            { label: "Phone", key: "phone", placeholder: "+918919767871", type: "tel" },
            { label: "Company", key: "company", placeholder: "Acme Corp", type: "text" },
          ].map(({ label, key, placeholder, type }) => (
            <div key={key}>
              <label className="text-[11px] font-bold text-gray-500 uppercase tracking-wide block mb-1">{label}</label>
              <input type={type} value={(form as any)[key]} onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                placeholder={placeholder}
                className="w-full bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-sm text-gray-800 outline-none focus:border-indigo-400 focus:bg-white transition-all" />
            </div>
          ))}

          <div>
            <label className="text-[11px] font-bold text-gray-500 uppercase tracking-wide block mb-1">Notes</label>
            <textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              placeholder="Any notes about this lead..."
              rows={2}
              className="w-full bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-sm text-gray-800 outline-none focus:border-indigo-400 focus:bg-white transition-all resize-none" />
          </div>

          {error && <p className="text-xs font-semibold text-red-600 bg-red-50 border border-red-200 rounded-xl px-3 py-2">{error}</p>}
        </div>

        <div className="flex items-center gap-3 px-6 pb-6">
          <button onClick={onClose} className="flex-1 bg-gray-100 text-gray-600 text-sm font-bold py-2.5 rounded-xl hover:bg-gray-200 transition-colors">
            Cancel
          </button>
          <button onClick={submit} disabled={loading}
            className="flex-1 bg-indigo-600 text-white text-sm font-bold py-2.5 rounded-xl hover:bg-indigo-700 transition-colors disabled:opacity-50">
            {loading ? "Adding..." : "Add Lead"}
          </button>
        </div>
      </div>
    </div>
  );
}
