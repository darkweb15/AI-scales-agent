"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Users, Bot, Calendar, BarChart3, Bell, Settings, ChevronLeft, ChevronRight, Zap, MessageSquare, Database } from "lucide-react";

const nav = [
  { icon: LayoutDashboard, label: "Dashboard",    href: "/",          badge: null,   color: "#4F8EF7" },
  { icon: Users,           label: "Leads",         href: "/leads",     badge: null,   color: "#A78BFA" },
  { icon: Database,        label: "Business Data", href: "/business",  badge: "26K",  color: "#34D399" },
  { icon: Bot,             label: "Agents",         href: "/agents",    badge: "6",    color: "#34D399" },
  { icon: Calendar,        label: "Demos",          href: "/demos",     badge: null,   color: "#34D399" },
  { icon: BarChart3,       label: "Analytics",      href: "/analytics", badge: null,   color: "#FBBF24" },
  { icon: MessageSquare,   label: "Campaigns",      href: "/campaigns", badge: null,   color: "#A78BFA" },
  { icon: Bell,            label: "Notifications",  href: "#",          badge: "3",    color: "#F87171" },
  { icon: Settings,        label: "Settings",       href: "#",          badge: null,   color: "#8888AA" },
];

export default function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const pathname = usePathname();
  return (
    <aside className={`flex flex-col bg-bg-surface border-r border-border transition-all duration-200 shrink-0 ${collapsed ? "w-14" : "w-56"}`}>
      <div className="flex items-center gap-2.5 px-4 h-14 border-b border-border shrink-0">
        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center shadow-lg shadow-accent-blue/20 shrink-0">
          <Zap size={16} className="text-white" />
        </div>
        {!collapsed && (
          <div>
            <div className="text-sm font-black text-text-primary leading-tight">SalesAI</div>
            <div className="text-[9px] font-bold text-text-muted tracking-widest uppercase">Agentic Platform</div>
          </div>
        )}
      </div>

      <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
        {nav.map(({ icon: Icon, label, href, badge, color }) => {
          const active = pathname === href || (href !== "/" && pathname.startsWith(href));
          return (
            <Link key={label} href={href} className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-[13px] transition-all ${
              active
                ? "bg-accent-blue/15 text-accent-blue font-semibold border border-accent-blue/20"
                : "text-text-secondary hover:bg-bg-elevated hover:text-text-primary font-medium border border-transparent"
            }`}>
              <Icon size={15} className="shrink-0" style={{ color: active ? "#4F8EF7" : color }} />
              {!collapsed && <span className="flex-1 text-left">{label}</span>}
              {!collapsed && badge && (
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                  active ? "bg-accent-blue/20 text-accent-blue" : "bg-bg-elevated text-text-muted"
                }`}>{badge}</span>
              )}
            </Link>
          );
        })}
      </nav>

      {!collapsed && (
        <div className="px-3 pb-3 border-t border-border pt-3">
          <div className="flex items-center gap-2.5 p-2 rounded-lg hover:bg-bg-elevated cursor-pointer transition-colors">
            <div className="relative shrink-0">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-accent-amber to-accent-red flex items-center justify-center text-white text-xs font-black">A</div>
              <div className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-accent-green rounded-full border-2 border-bg-surface" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-semibold text-text-primary truncate">Admin User</div>
              <div className="text-[10px] text-text-muted truncate">admin@salesai.com</div>
            </div>
          </div>
        </div>
      )}

      <button onClick={onToggle} className="flex items-center justify-center h-8 border-t border-border text-text-muted hover:text-accent-blue hover:bg-bg-elevated transition-colors text-xs gap-1 shrink-0">
        {collapsed ? <ChevronRight size={14} /> : <><ChevronLeft size={14} /><span className="font-medium">Collapse</span></>}
      </button>
    </aside>
  );
}
