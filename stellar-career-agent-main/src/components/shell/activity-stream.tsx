"use client";
import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";
import { Sparkles, Terminal } from "lucide-react";
import { listWorkflows, API_BASE } from "@/lib/api";

type ActivityEvent = {
  id: string;
  agent: string;
  time: string;
  kind: "discover" | "match" | "apply" | "interview" | "info";
  text: string;
};

const kindStyles: Record<ActivityEvent["kind"], string> = {
  discover: "bg-secondary text-secondary-foreground",
  match: "bg-accent text-accent-foreground",
  apply: "bg-foreground text-background",
  interview: "bg-card border border-accent text-accent",
  info: "bg-muted text-muted-foreground",
};

export function ActivityStream({ open }: { open: boolean }) {
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  useEffect(() => {
    async function checkActiveRun() {
      let runId = window.localStorage.getItem("aria.run_id");
      if (!runId) {
        try {
          const ws = await listWorkflows();
          if (ws.workflows && ws.workflows.length > 0) {
            runId = ws.workflows[0].run_id;
            if (runId) {
              window.localStorage.setItem("aria.run_id", runId);
            }
          }
        } catch (_) {}
      }
      if (runId) {
        setActiveRunId(runId);
      }
    }
    checkActiveRun();
  }, []);

  // Subscribe to real Agent WebSockets
  useEffect(() => {
    if (!activeRunId) return;

    const wsBase = API_BASE.replace(/^http/, "ws");
    const wsUrl = `${wsBase}/ws/${activeRunId}`;
    let ws: WebSocket;
    let reconnectTimeout: any;

    function connect() {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setEvents((prev) => [
          {
            id: `sys-${Date.now()}`,
            agent: "System",
            time: "Just now",
            kind: "info",
            text: "Connected to live agent pipeline stream.",
          },
          ...prev,
        ].slice(0, 14));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          let kind: ActivityEvent["kind"] = "info";
          
          if ((data.step || "").toLowerCase().includes("discover")) kind = "discover";
          else if ((data.step || "").toLowerCase().includes("match") || (data.step || "").toLowerCase().includes("score")) kind = "match";
          else if ((data.step || "").toLowerCase().includes("apply")) kind = "apply";

          setEvents((prev) => [
            {
              id: `live-${Date.now()}-${Math.random()}`,
              agent: data.step || "Aria",
              time: "Just now",
              kind,
              text: data.message || "",
            },
            ...prev,
          ].slice(0, 14));
        } catch (_) {}
      };

      ws.onerror = () => {
        console.error("Agent feed websocket error");
      };

      ws.onclose = () => {
        // Attempt reconnection after 5s
        reconnectTimeout = setTimeout(connect, 5000);
      };
    }

    connect();

    return () => {
      if (ws) ws.close();
      clearTimeout(reconnectTimeout);
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
                  className="w-full text-left rounded-xl px-3 py-2.5 hover:bg-sidebar-accent/60 transition-colors group"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className={`text-[10px] uppercase tracking-wider rounded-full px-2 py-0.5 ${kindStyles[e.kind]}`}>{e.agent}</span>
                    <span className="text-[11px] text-muted-foreground tabular-nums">{e.time}</span>
                  </div>
                  <p className="text-sm leading-snug group-hover:text-foreground">{e.text}</p>
                </motion.div>
              ))}
            </AnimatePresence>

            {events.length === 0 && (
              <div className="p-8 text-center text-xs text-muted-foreground flex flex-col items-center gap-2">
                <Terminal className="h-5 w-5 text-muted-foreground" />
                <span>No active log stream yet. Launch a search run to stream agent actions.</span>
              </div>
            )}
          </div>

          <div className="border-t border-border p-4">
            <div className="rounded-2xl bg-foreground text-background p-4 shadow-soft">
              <div className="flex items-center gap-2 text-xs text-background/70">
                <Sparkles className="h-3.5 w-3.5" />
                Live Monitoring
              </div>
              <p className="mt-2 text-sm leading-relaxed">Aria is ready to stream log steps from WeWorkRemotely, Glassdoor and Naukri crawlers.</p>
            </div>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
