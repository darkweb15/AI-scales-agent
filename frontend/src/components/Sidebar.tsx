"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Users, Bot, Calendar, BarChart3, Bell, Settings, ChevronLeft, ChevronRight, Zap, MessageSquare, Lightbulb, Database } from "lucide-react";

const nav = [
  { icon: LayoutDashboard, label: "Dashboard",    href: "/",          badge: null,   color: "#6366F1" },
  { icon: Users,           label: "Leads",         href: "/leads",     badge: null,   color: "#8B5CF6" },
  { icon: Database,        label: "Business Data", href: "/business",  badge: "26K",  color: "#06B6D4" },
  { icon: Bot,             label: "Agents",         href: "/agents",    badge: "6",    color: "#06B6D4" },
  { icon: Calendar,        label: "Demos",          href: "/demos",     badge: null,   color: "#10B981" },
  { icon: BarChart3,       label: "Analytics",      href: "/analytics", badge: null,   color: "#F59E0B" },
  { icon: MessageSquare,   label: "Campaigns",      href: "/campaigns", badge: null,   color: "#EC4899" },
  { icon: Lightbulb,       label: "AI Insights",    href: "#",          badge: "New",  color: "#8B5CF6" },
  { icon: Bell,            label: "Notifications",  href: "#",          badge: "5",    color: "#EF4444" },
  { icon: Settings,        label: "Settings",       href: "#",          badge: null,   color: "#94A3B8" },
];

export default function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const pathname = usePathname();
  return (
    <aside className={`flex flex-col bg-white border-r border-gray-200 transition-all duration-200 shrink-0 ${collapsed ? "w-14" : "w-56"}`}>
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-4 h-14 border-b border-gray-100 shrink-0">
        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-md shrink-0">
          <Zap size={16} className="text-white" />
        </div>
        {!collapsed && (
          <div>
            <div className="text-sm font-black text-gray-900 leading-tight">SalesAI</div>
            <div className="text-[9px] font-bold text-gray-400 tracking-widest uppercase">Agentic Platform</div>
          </div>
        )}
      </div>

      {/* Nav items */}
      <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
        {nav.map(({ icon: Icon, label, href, badge, color }) => {
          const active = pathname === href || (href !== "/" && pathname.startsWith(href));
          return (
            <Link key={label} href={href} className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-[13px] transition-all ${
              active
                ? "bg-indigo-600 text-white font-semibold shadow-sm"
                : "text-gray-500 hover:bg-gray-50 hover:text-gray-800 font-medium"
            }`}>
              <Icon size={15} className="shrink-0" style={{ color: active ? "white" : color }} />
              {!collapsed && <span className="flex-1 text-left">{label}</span>}
              {!collapsed && badge && (
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                  active ? "bg-white/20 text-white" : badge === "New" ? "bg-violet-100 text-violet-700" : "bg-gray-100 text-gray-500"
                }`}>{badge}</span>
              )}
            </Link>
          );
        })}
      </nav>



      {/* User */}
      {!collapsed && (
        <div className="px-3 pb-3 border-t border-gray-100 pt-3">
          <div className="flex items-center gap-2.5 p-2 rounded-lg hover:bg-gray-50 cursor-pointer">
            <div className="relative shrink-0">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-400 to-red-500 flex items-center justify-center text-white text-xs font-black">A</div>
              <div className="absolute bottom-0 right-0 w-2 h-2 bg-emerald-400 rounded-full border border-white" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-semibold text-gray-800 truncate">Admin User</div>
              <div className="text-[10px] text-gray-400 truncate">admin@salesai.com</div>
            </div>
          </div>
        </div>
      )}

      <button onClick={onToggle} className="flex items-center justify-center h-8 border-t border-gray-100 text-gray-400 hover:text-indigo-600 hover:bg-gray-50 transition-colors text-xs gap-1 shrink-0">
        {collapsed ? <ChevronRight size={14} /> : <><ChevronLeft size={14} /><span className="font-medium">Collapse</span></>}
      </button>
    </aside>
  );
}
