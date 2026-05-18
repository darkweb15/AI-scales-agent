"use client";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

const data = [
  { d: "Apr 18", calls: 42, emails: 120, demos: 8,  conv: 3 },
  { d: "Apr 19", calls: 58, emails: 145, demos: 11, conv: 4 },
  { d: "Apr 20", calls: 51, emails: 132, demos: 9,  conv: 3 },
  { d: "Apr 21", calls: 67, emails: 168, demos: 14, conv: 5 },
  { d: "Apr 22", calls: 73, emails: 189, demos: 16, conv: 6 },
  { d: "Apr 23", calls: 61, emails: 155, demos: 12, conv: 4 },
  { d: "Apr 24", calls: 84, emails: 210, demos: 18, conv: 7 },
];

const CustomTip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-2.5 shadow-lg text-xs">
      <p className="font-bold text-gray-700 mb-1.5">{label}</p>
      {payload.map((p: any) => (
        <div key={p.name} className="flex items-center gap-2 mb-0.5">
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
          <span className="text-gray-500 capitalize">{p.name}:</span>
          <span className="font-bold text-gray-800">{p.value}</span>
        </div>
      ))}
    </div>
  );
};

export default function ActivityOverview() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-gray-100">
        <div>
          <h2 className="text-sm font-bold text-gray-900">Activity Overview</h2>
          <p className="text-[11px] text-gray-400 mt-0.5">Last 7 days</p>
        </div>
      </div>
      <div className="p-4">
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={data} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis dataKey="d" tick={{ fontSize: 10, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 10, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTip />} />
            <Legend wrapperStyle={{ fontSize: 10, paddingTop: 8 }} />
            <Line type="monotone" dataKey="calls"  stroke="#6366F1" strokeWidth={2} dot={false} activeDot={{ r: 3 }} />
            <Line type="monotone" dataKey="emails" stroke="#10B981" strokeWidth={2} dot={false} activeDot={{ r: 3 }} />
            <Line type="monotone" dataKey="demos"  stroke="#F59E0B" strokeWidth={2} dot={false} activeDot={{ r: 3 }} />
            <Line type="monotone" dataKey="conv"   stroke="#8B5CF6" strokeWidth={2} dot={false} activeDot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
