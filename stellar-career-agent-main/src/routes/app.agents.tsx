"use client";
import { createFileRoute } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { Play, Pause, ArrowRight, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader } from "@/components/shell/sidebar";
import { Stagger, StaggerItem, HoverLift } from "@/components/motion/primitives";
import { getAgentsStatus } from "@/lib/api";

export const Route = createFileRoute("/app/agents")({
  head: () => ({
    meta: [
      { title: "AI Agents — Aria" },
      { name: "description", content: "Your AI career agents, working in concert." },
    ],
  }),
  component: AgentsPage,
});

const statusStyles: Record<string, string> = {
  active: "bg-accent text-accent-foreground",
  thinking: "bg-amber-500 text-white",
  idle: "bg-muted text-muted-foreground",
  done: "bg-emerald-500 text-white",
  error: "bg-red-500 text-white",
  paused: "bg-card border border-border text-muted-foreground",
};

const agentRoles: Record<string, string> = {
  resume: "Resume parser & profile optimizer",
  profiler: "Career profiling analyst",
  market: "Market demand researcher",
  discovery: "Job board discovery scraper",
  scoring: "Semantic score algorithm",
  coach: "LLM advisor & roadmapper",
  application: "Playwright auto-applier",
};

const agentDescriptions: Record<string, string> = {
  resume: "Analyzes skills, work experience, and projects. Generates ATS fit score and suggests modifications.",
  profiler: "Constructs ideal career paths, maps seniority, and compiles salary target estimates.",
  market: "Identifies trending skill gaps and recommended certifications based on target roles.",
  discovery: "Searches WeWorkRemotely, GlassDoor, and Naukri using priority criteria. Excludes simulated jobs.",
  scoring: "Performs semantic and keyword overlap comparison to rank jobs by overall match relevance.",
  coach: "Provides chat suggestions, tailors cover letters, and outlines structured learning roadmap steps.",
  application: "Automates application filings and surfaces security blocks for human verification.",
};

function AgentCard({ a }: { a: any }) {
  const status = a.status || "idle";
  const desc = agentDescriptions[a.agent_id] || "Coordinating pipeline tasks.";
  const roleName = agentRoles[a.agent_id] || "AI Career Specialist";

  return (
    <HoverLift>
      <div className="rounded-2xl border border-border bg-card p-6 shadow-soft hover:shadow-elegant transition-shadow h-full flex flex-col">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className={`text-[10px] uppercase tracking-wider rounded-full px-2 py-0.5 ${statusStyles[status] || "bg-muted text-muted-foreground"}`}>
                {status === "active" && (
                  <span className="relative inline-flex h-1.5 w-1.5 mr-1.5 align-middle">
                    <span className="absolute inline-flex h-full w-full rounded-full bg-current opacity-70 pulse-ring" />
                    <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-current" />
                  </span>
                )}
                {status}
              </span>
            </div>
            <div className="font-display text-xl">{a.name}</div>
            <div className="text-xs text-muted-foreground">{roleName}</div>
          </div>
        </div>

        <p className="text-sm text-foreground/80 flex-1">{desc}</p>

        <div className="mt-5 grid grid-cols-2 gap-3 text-xs">
          <div className="rounded-xl bg-muted/60 p-3">
            <div className="text-muted-foreground">Tasks today</div>
            <div className="font-display text-xl mt-0.5">{a.tasks_today || 0}</div>
          </div>
          <div className="rounded-xl bg-muted/60 p-3">
            <div className="text-muted-foreground">Lifetime</div>
            <div className="font-display text-xl mt-0.5">{a.tasks_total || 0}</div>
          </div>
        </div>

        {a.progress > 0 && a.progress < 100 && status !== "paused" && (
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

        {a.recent_actions && a.recent_actions.length > 0 && (
          <div className="mt-5 pt-4 border-t border-border space-y-1.5">
            <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground mb-2">Recent</div>
            {a.recent_actions.slice(0, 2).map((act: any, i: number) => (
              <div key={i} className="flex items-start gap-2 text-xs">
                <span className="text-muted-foreground tabular-nums w-12 flex-shrink-0">{act.time || "Now"}</span>
                <span className="text-foreground/80">{act.text}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </HoverLift>
  );
}

function Workflow() {
  const steps = ["Resume Parse", "Discovery", "Matching", "Auto Apply", "Tracking", "Interview"];
  return (
    <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
      <div className="flex items-center justify-between mb-4">
        <div className="font-display text-lg">Agent pipeline workflow</div>
        <span className="text-xs text-accent inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-accent pulse-ring relative" />
          Live state
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
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAgents() {
      try {
        const res = await getAgentsStatus();
        setAgents(res.agents || []);
      } catch (err) {
        console.error("Failed to load agents status", err);
      } finally {
        setLoading(false);
      }
    }
    loadAgents();
  }, []);

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-accent" />
          <span className="text-sm text-muted-foreground">Checking live agent status...</span>
        </div>
      </div>
    );
  }

  return (
    <>
      <PageHeader title="AI Agents" subtitle="Seven specialized agents collaborating on your career, 24/7." />
      <Workflow />
      <Stagger className="mt-6 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {agents.map((a) => (
          <StaggerItem key={a.agent_id}><AgentCard a={a} /></StaggerItem>
        ))}
      </Stagger>
    </>
  );
}
