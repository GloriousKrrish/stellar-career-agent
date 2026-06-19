"use client";
import { Bell, Command, Menu, Moon, PanelRight, Sun } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";

export function TopBar({
  onCommand,
  onMenu,
  onToggleActivity,
  activityOpen,
}: {
  onCommand: () => void;
  onMenu: () => void;
  onToggleActivity: () => void;
  activityOpen: boolean;
}) {
  const [dark, setDark] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);
  const [notifications, setNotifications] = useState<any[]>([]);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) setNotifOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const unread = notifications.filter((n) => n.unread).length;

  return (
    <header className="h-16 border-b border-border bg-background/80 backdrop-blur-xl flex items-center justify-between px-4 lg:px-6 sticky top-0 z-20">
      <div className="flex items-center gap-2">
        <button onClick={onMenu} className="lg:hidden inline-flex h-9 w-9 items-center justify-center rounded-md hover:bg-muted">
          <Menu className="h-4 w-4" />
        </button>
        <button
          onClick={onCommand}
          className="hidden md:inline-flex items-center gap-2 rounded-xl border border-border bg-muted/40 text-muted-foreground hover:text-foreground px-3 py-1.5 text-xs transition-colors"
        >
          <Command className="h-3.5 w-3.5" />
          <span>Quick search, jump to anything...</span>
          <kbd className="text-[10px] bg-card border border-border px-1.5 py-0.5 rounded">⌘K</kbd>
        </button>
      </div>

      <div className="flex items-center gap-1.5">
        <button
          onClick={() => setDark(!dark)}
          className="h-9 w-9 inline-flex items-center justify-center rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition"
          aria-label="Toggle theme"
        >
          {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>

        <div ref={notifRef} className="relative">
          <button
            onClick={() => setNotifOpen(!notifOpen)}
            className="h-9 w-9 inline-flex items-center justify-center rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition relative"
            aria-label="Notifications"
          >
            <Bell className="h-4 w-4" />
            {unread > 0 && (
              <span className="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full bg-accent" />
            )}
          </button>
          <AnimatePresence>
            {notifOpen && (
              <motion.div
                initial={{ opacity: 0, y: -4, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -4, scale: 0.98 }}
                transition={{ duration: 0.18 }}
                className="absolute right-0 top-11 w-80 rounded-2xl bg-popover border border-border shadow-glow overflow-hidden z-30"
              >
                <div className="px-4 py-3 border-b border-border flex items-center justify-between">
                  <div className="font-display text-sm">Notifications</div>
                  <button onClick={() => setNotifications([])} className="text-xs text-muted-foreground hover:text-foreground">Mark all read</button>
                </div>
                <div className="max-h-96 overflow-y-auto">
                  {notifications.map((n) => (
                    <div key={n.id} className="px-4 py-3 border-b border-border last:border-0 hover:bg-muted/60 cursor-pointer">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-start gap-2">
                          {n.unread && <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-accent flex-shrink-0" />}
                          <div className="text-sm font-medium">{n.title}</div>
                        </div>
                        <div className="text-[11px] text-muted-foreground">{n.time}</div>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground pl-3.5">{n.body}</p>
                    </div>
                  ))}
                  {notifications.length === 0 && (
                    <div className="p-8 text-center text-xs text-muted-foreground">
                      No notifications yet.
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <button
          onClick={onToggleActivity}
          className={`hidden xl:inline-flex h-9 w-9 items-center justify-center rounded-md transition ${
            activityOpen ? "bg-muted text-foreground" : "text-muted-foreground hover:text-foreground hover:bg-muted"
          }`}
          aria-label="Toggle activity stream"
        >
          <PanelRight className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
