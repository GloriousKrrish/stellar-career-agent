"use client";
import { useState, useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { Play, Pause, ArrowRight, RefreshCw } from "lucide-react";
import { PageHeader } from "@/components/shell/sidebar";
import { Stagger, StaggerItem, HoverLift } from "@/components/motion/primitives";
import { AGENTS } from "@/lib/mock/agents";
import { api } from "@/lib/api";
import type { Agent } from "@/lib/types";

export const Route = createFileRoute("/app/agents")({
  head: () => ({
    meta: [
      { title: "AI Agents — Aria" },
      { name: "description", content: "Your seven AI career agents, working in concert." },
    ],
  }),
  component: AgentsPage,
});

const statusStyles: Record<Agent["status"], string> = {
  active: "bg-accent text-accent-foreground",
  thinking: "bg-secondary text-secondary-foreground",
  idle: "bg-muted text-muted-foreground",
  paused: "bg-card border border-border text-muted-foreground",
};

function AgentCard({ a }: { a: Agent }) {
  return (
    <HoverLift>
      <div className="rounded-2xl border border-border bg-card p-6 shadow-soft hover:shadow-elegant transition-shadow h-full flex flex-col">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className={`text-[10px] uppercase tracking-wider rounded-full px-2 py-0.5 ${statusStyles[a.status]}`}>
                {a.status === "active" && (
                  <span className="relative inline-flex h-1.5 w-1.5 mr-1.5 align-middle">
                    <span className="absolute inline-flex h-full w-full rounded-full bg-current opacity-70 pulse-ring" />
                    <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-current" />
                  </span>
                )}
                {a.status}
              </span>
            </div>
            <div className="font-display text-xl">{a.name}</div>
            <div className="text-xs text-muted-foreground">{a.role}</div>
          </div>
          <button className="h-8 w-8 inline-flex items-center justify-center rounded-full border border-border hover:bg-muted text-muted-foreground">
            {a.status === "paused" ? <Play className="h-3.5 w-3.5" /> : <Pause className="h-3.5 w-3.5" />}
          </button>
        </div>

        <p className="text-sm text-foreground/80">{a.description}</p>

        <div className="mt-5 grid grid-cols-2 gap-3 text-xs">
          <div className="rounded-xl bg-muted/60 p-3">
            <div className="text-muted-foreground">Tasks today</div>
            <div className="font-display text-xl mt-0.5">{a.tasksToday.toLocaleString()}</div>
          </div>
          <div className="rounded-xl bg-muted/60 p-3">
            <div className="text-muted-foreground">Lifetime</div>
            <div className="font-display text-xl mt-0.5">{a.tasksTotal.toLocaleString()}</div>
          </div>
        </div>

        {a.progress < 100 && a.status !== "paused" && (
          <div className="mt-4">
            <div className="flex justify-between text-[11px] text-muted-foreground mb-1.5">
              <span>Working</span><span>{a.progress}%</span>
            </div>
            <div className="h-1 rounded-full bg-muted overflow-hidden">
              <motion.div
                initial={{ width: 0 }} animate={{ width: `${a.progress}%` }}
                transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
                className="h-full bg-accent"
              />
            </div>
          </div>
        )}

        <div className="mt-5 pt-4 border-t border-border space-y-1.5 flex-1">
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground mb-2">Recent</div>
          {a.recentActions.length === 0 && (
            <div className="text-xs text-muted-foreground italic">No recent activity</div>
          )}
          {a.recentActions.map((act, i) => (
            <div key={i} className="flex items-start gap-2 text-xs">
              <span className="text-muted-foreground tabular-nums w-12 flex-shrink-0">{act.time}</span>
              <span className="text-foreground/80">{act.text}</span>
            </div>
          ))}
        </div>
      </div>
    </HoverLift>
  );
}

function Workflow() {
  const steps = ["Resume", "Discovery", "Matching", "Orchestrator", "Auto Apply", "Tracking", "Interview"];
  return (
    <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
      <div className="flex items-center justify-between mb-4">
        <div className="font-display text-lg">Agent workflow</div>
        <span className="text-xs text-accent inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-accent pulse-ring relative" />
          Live
        </span>
      </div>
      <div className="flex items-center overflow-x-auto pb-2 gap-1">
        {steps.map((s, i) => (
          <div key={s} className="flex items-center gap-1 flex-shrink-0">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.4, delay: i * 0.08 }}
              className="rounded-xl bg-muted px-4 py-2.5 text-xs font-medium"
            >
              {s}
            </motion.div>
            {i < steps.length - 1 && <ArrowRight className="h-3 w-3 text-muted-foreground" />}
          </div>
        ))}
      </div>
    </div>
  );
}

function AgentsPage() {
  // Initialize with empty-metrics placeholders (no fake data)
  const [agents, setAgents] = useState<Agent[]>(AGENTS);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  useEffect(() => {
    let active = true;
    const fetchStats = async () => {
      try {
        const data = await api.getAgentsDashboard();
        if (active && data.agents) {
          setAgents(data.agents);
          setLastRefresh(new Date());
        }
      } catch (err) {
        console.error("Failed to fetch agent dashboard stats:", err);
        // On error, keep the zero-value placeholders — never show fake data
      } finally {
        if (active) setLoading(false);
      }
    };
    
    fetchStats();
    // Poll every 3s for live updates
    const interval = setInterval(fetchStats, 3000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  // Also listen for WebSocket application_completed events to force refetch
  useEffect(() => {
    const handler = () => {
      api.getAgentsDashboard().then((data) => {
        if (data.agents) setAgents(data.agents);
      }).catch(() => {});
    };
    window.addEventListener("aria:application_completed", handler);
    return () => window.removeEventListener("aria:application_completed", handler);
  }, []);

  return (
    <>
      <PageHeader title="AI Agents" subtitle="Eight specialists collaborating on your career, 24/7." />

      {/* Refresh indicator */}
      <div className="flex items-center justify-end gap-2 text-xs text-muted-foreground mb-2">
        <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
        {lastRefresh
          ? `Updated ${lastRefresh.toLocaleTimeString()}`
          : "Loading live data..."}
      </div>

      <Workflow />
      <Stagger className="mt-6 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {agents.map((a) => (
          <StaggerItem key={a.id}><AgentCard a={a} /></StaggerItem>
        ))}
      </Stagger>
    </>
  );
}
