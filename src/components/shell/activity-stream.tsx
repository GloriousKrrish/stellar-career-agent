"use client";
import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import type { ActivityEvent } from "@/lib/types";
import { ActivityDetailDialog } from "@/components/activity/activity-detail-dialog";
import { API_BASE_URL } from "@/lib/api";

const kindStyles: Record<ActivityEvent["kind"], string> = {
  discover: "bg-secondary text-secondary-foreground",
  match: "bg-accent text-accent-foreground",
  apply: "bg-foreground text-background",
  interview: "bg-card border border-accent text-accent",
  info: "bg-muted text-muted-foreground",
};

const mapEventKind = (agent: string, eventType: string): ActivityEvent["kind"] => {
  const ag = agent.toLowerCase();
  const ev = eventType.toLowerCase();
  if (ag.includes("discovery") || ag.includes("market") || ev.includes("found")) return "discover";
  if (ag.includes("scoring") || ev.includes("scored") || ev.includes("match")) return "match";
  if (ag.includes("apply") || ag.includes("application")) return "apply";
  if (ag.includes("coach") || ag.includes("interview") || ag.includes("tracking")) return "interview";
  return "info";
};

export function ActivityStream({ open }: { open: boolean }) {
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [active, setActive] = useState<ActivityEvent | null>(null);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const runId = localStorage.getItem("aria.active_run_id");
    setActiveRunId(runId);

    const handleRunStarted = (e: Event) => {
      const customEvent = e as CustomEvent;
      setActiveRunId(customEvent.detail);
    };

    window.addEventListener("aria:run_started", handleRunStarted);
    return () => {
      window.removeEventListener("aria:run_started", handleRunStarted);
    };
  }, []);

  useEffect(() => {
    if (!activeRunId) {
      setEvents([]);
      return;
    }

    const wsBase = API_BASE_URL ? API_BASE_URL.replace(/^http/, "ws") : "ws://localhost:8000";
    const socket = new WebSocket(`${wsBase}/ws/${activeRunId}`);

    socket.onopen = () => {
      console.log("WebSocket connected to run:", activeRunId);
      setEvents([
        {
          id: "conn-start",
          agent: "Orchestrator",
          text: "Connected to career agent. Standing by...",
          time: "Just now",
          kind: "info",
        },
      ]);
    };

    socket.onmessage = (event) => {
      try {
        const raw = JSON.parse(event.data);
        const mapped: ActivityEvent = {
          id: raw.id || `ws-${Date.now()}-${Math.random()}`,
          agent: raw.agent || "Orchestrator",
          text: raw.message || "",
          time: "Just now",
          kind: mapEventKind(raw.agent || "", raw.event_type || ""),
        };
        
        setEvents((prev) => {
          if (prev.some(p => p.text === mapped.text)) return prev;
          return [mapped, ...prev].slice(0, 20);
        });

        // Dispatch a custom window event to trigger dashboard/Kanban board refetches
        if (raw.event_type === "application_completed") {
          window.dispatchEvent(new CustomEvent("aria:application_completed", { detail: raw.data }));
        }

        if (raw.event_type === "completed" || raw.event_type === "error") {
          localStorage.removeItem("aria.active_run_id");
          setTimeout(() => setActiveRunId(null), 5000);
        }
      } catch (err) {
        console.error("Failed to parse WebSocket message:", err);
      }
    };

    socket.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    socket.onclose = () => {
      console.log("WebSocket connection closed");
    };

    return () => {
      socket.close();
    };
  }, [activeRunId]);

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
                <span className={`absolute inline-flex h-full w-full rounded-full bg-accent ${activeRunId ? "pulse-ring" : ""}`} />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
              </span>
              {activeRunId ? "Running" : "Idle"}
            </span>
          </div>

          <div className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
            <AnimatePresence initial={false}>
              {events.map((e) => (
                <motion.button
                  key={e.id}
                  layout
                  type="button"
                  onClick={() => setActive(e)}
                  initial={{ opacity: 0, y: -8, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
                  className="w-full text-left rounded-xl px-3 py-2.5 hover:bg-sidebar-accent/60 transition-colors group cursor-pointer"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className={`text-[10px] uppercase tracking-wider rounded-full px-2 py-0.5 ${kindStyles[e.kind]}`}>{e.agent}</span>
                    <span className="text-[11px] text-muted-foreground tabular-nums">{e.time}</span>
                  </div>
                  <p className="text-sm leading-snug group-hover:text-foreground">{e.text}</p>
                </motion.button>
              ))}
            </AnimatePresence>
            {events.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-center text-muted-foreground text-xs p-6 pt-24">
                <Sparkles className="h-8 w-8 mb-3 opacity-30 text-accent" />
                <p className="font-medium text-foreground">Feed is quiet</p>
                <p className="mt-1">Agents are standing by. Launch a search or upload a resume to see real-time updates.</p>
              </div>
            )}
          </div>

          <div className="border-t border-border p-4">
            <div className="rounded-2xl bg-foreground text-background p-4">
              <div className="flex items-center gap-2 text-xs text-background/70">
                <Sparkles className="h-3.5 w-3.5" />
                Ask Aria
              </div>
              <p className="mt-2 text-sm">Try: "Why did the OpenAI role match so well?"</p>
              <button className="mt-3 w-full rounded-lg bg-background/10 hover:bg-background/20 transition py-2 text-xs cursor-pointer">Open chat</button>
            </div>
          </div>
        </motion.aside>
      )}
      <ActivityDetailDialog event={active} onClose={() => setActive(null)} />
    </AnimatePresence>
  );
}
