"use client";
import { Command } from "cmdk";
import { useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { LayoutDashboard, Search, Bot, Briefcase, FileText, Mail, MessageSquare, LineChart, Settings, ArrowRight } from "lucide-react";

const commands = [
  { label: "Dashboard", to: "/app/dashboard", icon: LayoutDashboard, group: "Navigate" },
  { label: "Job Search", to: "/app/jobs", icon: Search, group: "Navigate" },
  { label: "AI Agents", to: "/app/agents", icon: Bot, group: "Navigate" },
  { label: "Applications", to: "/app/applications", icon: Briefcase, group: "Navigate" },
  { label: "Resume Analyzer", to: "/app/resume", icon: FileText, group: "Navigate" },
  { label: "Cover Letters", to: "/app/cover-letters", icon: Mail, group: "Navigate" },
  { label: "Interview Prep", to: "/app/interview-prep", icon: MessageSquare, group: "Navigate" },
  { label: "Analytics", to: "/app/analytics", icon: LineChart, group: "Navigate" },
  { label: "Settings", to: "/app/settings", icon: Settings, group: "Navigate" },
] as const;

export function CommandPalette({ open, setOpen }: { open: boolean; setOpen: (v: boolean) => void }) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen(!open);
      }
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, setOpen]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 bg-foreground/30 backdrop-blur-sm flex items-start justify-center pt-[15vh] px-4"
          onClick={() => setOpen(false)}
        >
          <motion.div
            initial={{ y: -10, scale: 0.98, opacity: 0 }}
            animate={{ y: 0, scale: 1, opacity: 1 }}
            exit={{ y: -10, scale: 0.98, opacity: 0 }}
            transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-xl rounded-2xl bg-card border border-border shadow-glow overflow-hidden"
          >
            <Command label="Command palette" className="w-full">
              <Command.Input
                value={query}
                onValueChange={setQuery}
                placeholder="Search jobs, agents, settings..."
                className="w-full px-5 py-4 text-sm bg-transparent border-b border-border outline-none placeholder:text-muted-foreground"
              />
              <Command.List className="max-h-[400px] overflow-y-auto p-2">
                <Command.Empty className="py-10 text-center text-sm text-muted-foreground">No results found.</Command.Empty>
                <Command.Group heading="Navigate" className="text-xs text-muted-foreground px-2 py-1.5 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.14em] [&_[cmdk-group-heading]]:mb-1">
                  {commands.map((c) => (
                    <Command.Item
                      key={c.to}
                      value={c.label}
                      onSelect={() => { navigate({ to: c.to }); setOpen(false); }}
                      className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm aria-selected:bg-muted cursor-pointer"
                    >
                      <c.icon className="h-4 w-4 text-muted-foreground" />
                      <span className="flex-1">{c.label}</span>
                      <ArrowRight className="h-3.5 w-3.5 text-muted-foreground opacity-0 aria-selected:opacity-100" />
                    </Command.Item>
                  ))}
                </Command.Group>
              </Command.List>
              <div className="px-3 py-2 border-t border-border text-[11px] text-muted-foreground flex items-center justify-between">
                <span>↑↓ navigate · ↵ open</span>
                <kbd className="px-1.5 py-0.5 bg-muted rounded">esc</kbd>
              </div>
            </Command>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
