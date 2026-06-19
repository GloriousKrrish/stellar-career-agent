"use client";
import { Link, useRouterState, useNavigate } from "@tanstack/react-router";
import { LayoutDashboard, Search, Bot, Briefcase, FileText, Mail, MessageSquare, LineChart, Settings, LogOut, ChevronsLeft, ChevronsRight, Command } from "lucide-react";
import { useState, useEffect, type ReactNode } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Logo } from "@/components/brand/logo";
import { signOut } from "@/lib/auth";
import { getMe } from "@/lib/api";

const items = [
  { to: "/app/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/app/jobs", label: "Job Search", icon: Search },
  { to: "/app/agents", label: "AI Agents", icon: Bot },
  { to: "/app/applications", label: "Applications", icon: Briefcase },
  { to: "/app/resume", label: "Resume Analyzer", icon: FileText },
  { to: "/app/cover-letters", label: "Cover Letters", icon: Mail },
  { to: "/app/interview-prep", label: "Interview Prep", icon: MessageSquare },
  { to: "/app/analytics", label: "Analytics", icon: LineChart },
  { to: "/app/settings", label: "Settings", icon: Settings },
] as const;

export function Sidebar({
  collapsed,
  setCollapsed,
  onCommand,
}: {
  collapsed: boolean;
  setCollapsed: (v: boolean) => void;
  onCommand: () => void;
}) {
  const path = useRouterState({ select: (s) => s.location.pathname });
  const navigate = useNavigate();
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    async function loadUser() {
      try {
        const u = await getMe();
        setUser(u);
      } catch (_) {}
    }
    loadUser();

    // Listen to auth changes
    window.addEventListener("auth-change", loadUser);
    return () => {
      window.removeEventListener("auth-change", loadUser);
    };
  }, []);

  const initials = user?.name ? user.name.split(" ").map((n: string) => n[0]).join("").toUpperCase() : "U";

  return (
    <aside
      className={`hidden lg:flex flex-col gap-2 border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-[width] duration-300 ${
        collapsed ? "w-[72px]" : "w-[248px]"
      }`}
    >
      <div className="flex items-center justify-between px-4 h-16 border-b border-sidebar-border">
        {!collapsed ? <Logo /> : <div className="mx-auto"><Logo /></div>}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="hidden xl:inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-sidebar-accent"
          aria-label="Toggle sidebar"
        >
          {collapsed ? <ChevronsRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
        </button>
      </div>

      <button
        onClick={onCommand}
        className={`mx-3 mt-3 flex items-center gap-2 rounded-xl border border-sidebar-border bg-card/40 text-muted-foreground hover:text-foreground hover:bg-card transition-colors px-3 py-2 text-xs ${
          collapsed ? "justify-center" : ""
        }`}
      >
        <Command className="h-3.5 w-3.5" />
        {!collapsed && <>
          <span className="flex-1 text-left">Quick search</span>
          <kbd className="text-[10px] bg-muted px-1.5 py-0.5 rounded">⌘K</kbd>
        </>}
      </button>

      <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
        {items.map((item) => {
          const active = path === item.to || (item.to !== "/app/dashboard" && path.startsWith(item.to));
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`group relative flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition-colors ${
                active ? "bg-sidebar-accent text-sidebar-accent-foreground" : "text-muted-foreground hover:text-foreground hover:bg-sidebar-accent/60"
              } ${collapsed ? "justify-center" : ""}`}
              title={collapsed ? item.label : undefined}
            >
              {active && (
                <motion.span
                  layoutId="sidebar-active"
                  className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-0.5 rounded-r-full bg-accent"
                  transition={{ type: "spring", stiffness: 380, damping: 30 }}
                />
              )}
              <item.icon className={`h-4 w-4 flex-shrink-0 ${active ? "text-accent" : ""}`} />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      <div className="px-3 pb-3 border-t border-sidebar-border pt-3">
        <div className={`flex items-center gap-3 rounded-xl px-2 py-2 ${collapsed ? "justify-center" : ""}`}>
          <div className="h-8 w-8 rounded-full bg-foreground text-background flex items-center justify-center text-xs font-display shrink-0">
            {initials}
          </div>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate">{user?.name || "Aria User"}</div>
              <div className="text-xs text-muted-foreground truncate">{user?.email || ""}</div>
            </div>
          )}
          {!collapsed && (
            <button
              onClick={() => { signOut(); navigate({ to: "/auth/login" }); }}
              className="h-7 w-7 inline-flex items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
              aria-label="Sign out"
            >
              <LogOut className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="flex items-end justify-between gap-4 flex-wrap mb-8">
      <div>
        <h1 className="font-display text-3xl tracking-tight">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function PageTransition({ children, k }: { children: ReactNode; k: string }) {
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={k}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -4 }}
        transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
