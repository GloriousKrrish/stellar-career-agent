"use client";
import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import { ACTIVITY } from "@/lib/mock/agents";
import type { ActivityEvent } from "@/lib/types";
import { ActivityDetailDialog } from "@/components/activity/activity-detail-dialog";

const kindStyles: Record<ActivityEvent["kind"], string> = {
  discover: "bg-secondary text-secondary-foreground",
  match: "bg-accent text-accent-foreground",
  apply: "bg-foreground text-background",
  interview: "bg-card border border-accent text-accent",
  info: "bg-muted text-muted-foreground",
};

export function ActivityStream({ open }: { open: boolean }) {
  const [events, setEvents] = useState(ACTIVITY);
  const [active, setActive] = useState<ActivityEvent | null>(null);

  // Simulate live events
  useEffect(() => {
    const id = setInterval(() => {
      setEvents((prev) => {
        const next = [...prev];
        const ev = { ...next[next.length - 1], id: `live-${Date.now()}`, time: "Just now" };
        return [{ ...ev, agent: ["Discovery", "Matching", "Auto Apply", "Tracking"][Math.floor(Math.random() * 4)] }, ...next].slice(0, 14);
      });
    }, 8000);
    return () => clearInterval(id);
  }, []);

  return (
    <AnimatePresence>
      {open && (
        <motion.aside
          initial={{ x: 40, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 40, opacity: 0 }}
          transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
          className="hidden xl:flex flex-col border-l border-border bg-sidebar w-[320px] flex-shrink-0"
        >
          <div className="flex items-center justify-between px-5 h-16 border-b border-border">
            <div>
              <div className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Activity</div>
              <div className="font-display text-sm">Agents live feed</div>
            </div>
            <span className="inline-flex items-center gap-1.5 text-xs text-accent">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full rounded-full bg-accent pulse-ring" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
              </span>
              Live
            </span>
          </div>

          <div className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
            <AnimatePresence initial={false}>
              {events.map((e) => (
                <motion.div
                  key={e.id}
                  layout
                  initial={{ opacity: 0, y: -8, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
                  className="rounded-xl px-3 py-2.5 hover:bg-sidebar-accent/60 transition-colors"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className={`text-[10px] uppercase tracking-wider rounded-full px-2 py-0.5 ${kindStyles[e.kind]}`}>{e.agent}</span>
                    <span className="text-[11px] text-muted-foreground tabular-nums">{e.time}</span>
                  </div>
                  <p className="text-sm leading-snug">{e.text}</p>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>

          <div className="border-t border-border p-4">
            <div className="rounded-2xl bg-foreground text-background p-4">
              <div className="flex items-center gap-2 text-xs text-background/70">
                <Sparkles className="h-3.5 w-3.5" />
                Ask Aria
              </div>
              <p className="mt-2 text-sm">Try: "Why did the OpenAI role match so well?"</p>
              <button className="mt-3 w-full rounded-lg bg-background/10 hover:bg-background/20 transition py-2 text-xs">Open chat</button>
            </div>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
