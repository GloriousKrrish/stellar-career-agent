"use client";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Briefcase, Send, MessageCircle, TrendingUp, ArrowUpRight } from "lucide-react";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { PageHeader } from "@/components/shell/sidebar";
import { AnimatedCounter } from "@/components/motion/counter";
import { Stagger, StaggerItem, HoverLift } from "@/components/motion/primitives";
import { api } from "@/lib/api";
import { getCurrentUser } from "@/lib/auth";
import { useEffect, useState } from "react";
import { AGENTS } from "@/lib/mock/agents";

export const Route = createFileRoute("/app/dashboard")({
  head: () => ({
    meta: [
      { title: "Dashboard — Aria" },
      { name: "description", content: "Your AI career command center." },
    ],
  }),
  component: Dashboard,
});

function MetricCard({ label, value, delta, icon: Icon, suffix }: { label: string; value: number; delta: string; icon: any; suffix?: string }) {
  return (
    <HoverLift>
      <div className="rounded-2xl border border-border bg-card p-5 shadow-soft hover:shadow-elegant transition-shadow">
        <div className="flex items-center justify-between mb-4">
          <div className="h-9 w-9 rounded-xl bg-muted flex items-center justify-center">
            <Icon className="h-4 w-4 text-accent" />
          </div>
          <span className="text-xs text-accent inline-flex items-center gap-0.5">
            <ArrowUpRight className="h-3 w-3" /> {delta}
          </span>
        </div>
        <div className="font-display text-3xl tracking-tight">
          <AnimatedCounter value={value} />{suffix}
        </div>
        <div className="text-xs text-muted-foreground mt-1">{label}</div>
      </div>
    </HoverLift>
  );
}

function RadialProgress({ value, label }: { value: number; label: string }) {
  const r = 56;
  const c = 2 * Math.PI * r;
  return (
    <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
      <div className="text-xs uppercase tracking-[0.14em] text-muted-foreground">{label}</div>
      <div className="mt-4 flex items-center gap-5">
        <div className="relative h-32 w-32">
          <svg viewBox="0 0 140 140" className="h-full w-full -rotate-90">
            <circle cx="70" cy="70" r={r} stroke="oklch(0.91 0.012 75)" strokeWidth="10" fill="none" />
            <circle cx="70" cy="70" r={r} stroke="oklch(0.62 0.07 55)" strokeWidth="10" strokeLinecap="round" fill="none"
              strokeDasharray={c} strokeDashoffset={c * (1 - value / 100)} />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <div className="font-display text-3xl"><AnimatedCounter value={value} />%</div>
          </div>
        </div>
        <div className="space-y-2 text-sm">
          <div><span className="text-muted-foreground">Industry avg</span> <span className="font-medium">12%</span></div>
          <div><span className="text-muted-foreground">Your rate</span> <span className="font-medium text-accent">{value}%</span></div>
          <div className="text-xs text-muted-foreground pt-1">2.1× above benchmark</div>
        </div>
      </div>
    </div>
  );
}

function Dashboard() {
  const navigate = useNavigate();
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [applications, setApplications] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 1. Get local user
    const localUser = getCurrentUser();
    if (localUser) {
      setCurrentUser(localUser);
    }

    async function loadAllData() {
      try {
        const user = await api.getMe();
        setCurrentUser(user);
      } catch (err) {
        console.error("Failed to load user info:", err);
      }

      try {
        const res = await api.getWorkflows();
        setWorkflows(res.workflows || []);
      } catch (err) {
        console.error("Failed to load workflows:", err);
      }

      try {
        const res = await api.getApplications();
        setApplications(res.applications || []);
      } catch (err) {
        console.error("Failed to load applications:", err);
      }

      try {
        const res = await api.getAgentStatus();
        setAgents(res.agents || []);
      } catch (err) {
        console.error("Failed to load agents status:", err);
      }

      setLoading(false);
    }

    loadAllData();
  }, []);

  // Compute metrics
  const jobsFound = workflows.reduce((sum, w) => sum + (w.jobs_found || 0), 0);
  const applicationsSent = applications.length;
  const interviewsCount = applications.filter((a) => a.stage === "interview").length;
  
  const activeApps = applications.filter((a) => a.stage !== "saved");
  const respondedApps = applications.filter((a) =>
    ["assessment", "interview", "offer", "rejected"].includes(a.stage)
  );
  const responseRate = activeApps.length > 0 ? Math.round((respondedApps.length / activeApps.length) * 100) : 0;

  // Weekdays chart
  const weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const growthData = weekdays.map((day) => {
    const count = applications.filter((app) => {
      if (!app.updatedAt) return false;
      const date = new Date(app.updatedAt);
      return weekdays[date.getDay()] === day;
    }).length;
    return { day, applications: count };
  });

  const cards = [
    { label: "Jobs found", value: jobsFound, delta: workflows.length > 0 ? `+${workflows.length} searches` : "0 active searches", icon: Briefcase },
    { label: "Applications sent", value: applicationsSent, delta: `Total tracked`, icon: Send },
    { label: "Interviews", value: interviewsCount, delta: `${interviewsCount} scheduled`, icon: MessageCircle },
    { label: "Response rate", value: responseRate, suffix: "%", delta: activeApps.length > 0 ? `${respondedApps.length} of ${activeApps.length} active` : "No applications", icon: TrendingUp },
  ];

  const displayAgents = agents.length > 0 ? agents : AGENTS.map(a => ({
    agent_id: a.id,
    name: a.name,
    status: a.status,
    recent_actions: a.recentActions,
    tasks_today: a.tasksToday,
  }));

  const activeAgentsCount = displayAgents.filter(a => a.status === "active" || a.status === "thinking").length;
  const firstName = currentUser?.name?.split(" ")[0] || "User";

  return (
    <>
      <PageHeader
        title={`Welcome back, ${firstName}.`}
        subtitle={workflows.length > 0 ? `Your agents discovered ${jobsFound} roles from your last search.` : "No active searches. Start a new search to discover roles."}
        actions={
          <button
            onClick={() => navigate({ to: "/app/onboarding" })}
            className="rounded-full bg-foreground text-background px-4 py-2 text-sm font-medium hover:opacity-90 cursor-pointer"
          >
            New search
          </button>
        }
      />

      <Stagger className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((c) => (
          <StaggerItem key={c.label}>
            <MetricCard {...c} />
          </StaggerItem>
        ))}
      </Stagger>

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 rounded-2xl border border-border bg-card p-6 shadow-soft">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Applications</div>
              <div className="font-display text-xl">Past 7 days</div>
            </div>
            <div className="flex gap-2 text-xs">
              {["7d", "30d", "90d"].map((t, i) => (
                <button key={t} className={`px-2.5 py-1 rounded-md ${i === 0 ? "bg-muted text-foreground" : "text-muted-foreground hover:bg-muted"}`}>{t}</button>
              ))}
            </div>
          </div>
          <div className="h-64 -mx-3">
            {applicationsSent === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-muted-foreground text-sm p-4">
                <Send className="h-8 w-8 mb-2 opacity-40 text-accent" />
                <p>No applications logged yet.</p>
                <p className="text-xs text-muted-foreground/80 mt-1">Once you apply to jobs, your weekly progress will appear here.</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={growthData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="a" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="oklch(0.62 0.07 55)" stopOpacity={0.5} />
                      <stop offset="100%" stopColor="oklch(0.62 0.07 55)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="oklch(0.91 0.012 75)" vertical={false} />
                  <XAxis dataKey="day" stroke="oklch(0.5 0.012 60)" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis stroke="oklch(0.5 0.012 60)" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: "oklch(1 0 0)", border: "1px solid oklch(0.91 0.012 75)", borderRadius: 12, fontSize: 12 }} />
                  <Area type="monotone" dataKey="applications" stroke="oklch(0.62 0.07 55)" strokeWidth={2} fill="url(#a)" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <RadialProgress value={responseRate} label="Response rate" />
      </div>

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
          <div className="flex items-center justify-between mb-4">
            <div className="font-display text-lg">Agents at work</div>
            <span className="text-xs text-accent">{activeAgentsCount} active</span>
          </div>
          <div className="space-y-3">
            {displayAgents.slice(0, 4).map((a: any) => (
              <div key={a.agent_id} className="flex items-center gap-3 py-2">
                <span className={`h-2 w-2 rounded-full ${a.status === "active" ? "bg-accent animate-pulse" : a.status === "thinking" ? "bg-secondary animate-pulse" : "bg-muted"}`} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{a.name}</div>
                  <div className="text-xs text-muted-foreground truncate">
                    {a.recent_actions?.[0]?.text || a.recentActions?.[0]?.text || (a.status === "active" ? "Working..." : "Idle")}
                  </div>
                </div>
                <div className="text-xs text-muted-foreground tabular-nums">{a.tasks_today ?? a.tasksToday ?? 0}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-foreground text-background p-6 shadow-elegant overflow-hidden relative">
          <div className="absolute -top-10 -right-10 h-40 w-40 rounded-full blur-3xl opacity-30"
            style={{ background: "radial-gradient(circle, oklch(0.7 0.07 55), transparent 70%)" }} />
          <div className="text-xs uppercase tracking-[0.14em] text-background/60">This week</div>
          <div className="font-display text-2xl mt-2 max-w-sm">You're trending toward your highest week ever.</div>
          <div className="mt-6 flex items-end gap-1 h-24">
            {growthData.map((d, i) => {
              const maxCount = Math.max(...growthData.map(gd => gd.applications), 1);
              const heightPct = Math.max(10, (d.applications / maxCount) * 100);
              return (
                <div key={i} className="flex-1 rounded-md bg-background/15 relative overflow-hidden h-full">
                  <div className="absolute bottom-0 inset-x-0 bg-accent transition-all" style={{ height: `${heightPct}%` }} />
                </div>
              );
            })}
          </div>
          <div className="mt-3 grid grid-cols-7 gap-1 text-[10px] text-background/50 text-center">
            {["S","M","T","W","T","F","S"].map((d, i) => <div key={i}>{d}</div>)}
          </div>
        </div>
      </div>
    </>
  );
}
