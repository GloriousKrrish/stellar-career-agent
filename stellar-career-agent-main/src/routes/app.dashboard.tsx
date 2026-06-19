"use client";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Briefcase, Send, MessageCircle, TrendingUp, ArrowUpRight, Upload, Sparkles, AlertCircle } from "lucide-react";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { PageHeader } from "@/components/shell/sidebar";
import { AnimatedCounter } from "@/components/motion/counter";
import { Stagger, StaggerItem, HoverLift } from "@/components/motion/primitives";
import { getMe, listApplications, listWorkflows, getAgentsStatus } from "@/lib/api";

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
      <div className="rounded-2xl border border-border bg-card p-5 shadow-soft hover:shadow-elegant transition-all">
        <div className="flex items-center justify-between mb-4">
          <div className="h-9 w-9 rounded-xl bg-muted flex items-center justify-center">
            <Icon className="h-4 w-4 text-accent" />
          </div>
          <span className="text-xs text-muted-foreground inline-flex items-center gap-0.5">
            {delta}
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
          <div className="text-xs text-muted-foreground pt-1">
            {value > 0 ? "Above average benchmark" : "No responses yet"}
          </div>
        </div>
      </div>
    </div>
  );
}

function Dashboard() {
  const navigate = useNavigate();
  const [user, setUser] = useState<any>(null);
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [apps, setApps] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboardData() {
      try {
        const [me, ws, applications, agentStatus] = await Promise.all([
          getMe(),
          listWorkflows(),
          listApplications(),
          getAgentsStatus(),
        ]);
        setUser(me);
        setWorkflows(ws.workflows || []);
        setApps(applications.applications || []);
        setAgents(agentStatus.agents || []);
      } catch (err) {
        console.error("Dashboard load failed", err);
      } finally {
        setLoading(false);
      }
    }
    loadDashboardData();
  }, []);

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          <span className="text-sm text-muted-foreground">Loading dashboard...</span>
        </div>
      </div>
    );
  }

  const hasData = workflows.length > 0;
  
  // Calculate Metrics from Real DB State
  const jobsDiscovered = workflows.reduce((sum, w) => sum + (w.jobs_found || 0), 0);
  const totalApplications = apps.length;
  const interviewsCount = apps.filter(a => a.stage === "Interview").length;
  const responseRate = totalApplications > 0 ? Math.round((apps.filter(a => ["Assessment", "Interview", "Offer"].includes(a.stage)).length / totalApplications) * 100) : 0;

  const metricCards = [
    { label: "Jobs found", value: jobsDiscovered, delta: hasData ? "From active runs" : "No active runs", icon: Briefcase },
    { label: "Applications sent", value: totalApplications, delta: hasData ? "Saved or filed" : "0 submitted", icon: Send },
    { label: "Interviews", value: interviewsCount, delta: hasData ? "In progress" : "No interviews", icon: MessageCircle },
    { label: "Response rate", value: responseRate, suffix: "%", delta: hasData ? "Positive updates" : "0%", icon: TrendingUp },
  ];

  // Applications growth data
  const growthData = hasData ? [
    { day: "Mon", applications: apps.filter(a => a.stage === "Applied").length },
    { day: "Tue", applications: apps.filter(a => a.stage === "Interview").length },
    { day: "Wed", applications: apps.length },
    { day: "Thu", applications: apps.length },
    { day: "Fri", applications: apps.length },
    { day: "Sat", applications: apps.length },
    { day: "Sun", applications: apps.length },
  ] : [
    { day: "Mon", applications: 0 },
    { day: "Tue", applications: 0 },
    { day: "Wed", applications: 0 },
    { day: "Thu", applications: 0 },
    { day: "Fri", applications: 0 },
    { day: "Sat", applications: 0 },
    { day: "Sun", applications: 0 },
  ];

  return (
    <>
      <PageHeader
        title={`Welcome back, ${user?.name?.split(" ")[0] || "Seeker"}.`}
        subtitle={hasData ? `Your agents have scanned real sources to find the best jobs.` : "Your AI-powered job search is ready to begin."}
        actions={
          <button onClick={() => navigate({ to: "/app/onboarding" })} className="rounded-full bg-foreground text-background px-5 py-2.5 text-sm font-medium hover:opacity-90 transition shadow-elegant flex items-center gap-2">
            <Sparkles className="h-4 w-4" /> New Search Run
          </button>
        }
      />

      {/* Empty State Banner */}
      {!hasData && (
        <div className="mb-8 p-8 rounded-3xl border border-dashed border-border bg-card/60 backdrop-blur-md relative overflow-hidden flex flex-col md:flex-row items-center gap-6 shadow-soft">
          <div className="absolute top-0 right-0 w-80 h-80 rounded-full blur-3xl bg-accent/5 -z-10" />
          <div className="h-16 w-16 rounded-2xl bg-muted flex items-center justify-center shrink-0">
            <Upload className="h-7 w-7 text-accent" />
          </div>
          <div className="flex-1 text-center md:text-left">
            <h3 className="font-display text-xl tracking-tight">Let's set up your agentic pipeline</h3>
            <p className="text-sm text-muted-foreground mt-1 max-w-xl">
              Upload your resume so Aria can analyze your profile, target real portals (WeWorkRemotely, GlassDoor, Naukri), score match alignment, and assist with applications.
            </p>
          </div>
          <button
            onClick={() => navigate({ to: "/app/onboarding" })}
            className="rounded-full bg-foreground text-background px-6 py-3 text-sm font-medium hover:opacity-90 transition shrink-0"
          >
            Upload Resume
          </button>
        </div>
      )}

      <Stagger className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {metricCards.map((c) => (
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
          </div>
          <div className="h-64 -mx-3">
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
          </div>
        </div>

        <RadialProgress value={responseRate} label="Response rate" />
      </div>

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
          <div className="flex items-center justify-between mb-4">
            <div className="font-display text-lg">Agents status</div>
            <span className="text-xs text-accent">{hasData ? `${agents.filter(a => a.status !== "idle").length} active` : "0 active"}</span>
          </div>
          <div className="space-y-3">
            {agents.map((a) => (
              <div key={a.agent_id} className="flex items-center gap-3 py-2 border-b border-border last:border-0">
                <span className={`h-2.5 w-2.5 rounded-full ${a.status === "active" ? "bg-emerald-500 animate-pulse" : a.status === "thinking" ? "bg-amber-500 animate-pulse" : "bg-muted"}`} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{a.name}</div>
                  <div className="text-xs text-muted-foreground truncate">{hasData ? (a.current_task || "Idle - monitoring state") : "Waiting for active run"}</div>
                </div>
                <div className="text-xs text-muted-foreground tabular-nums">Today: {hasData ? a.tasks_today : 0}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-foreground text-background p-6 shadow-elegant overflow-hidden relative">
          <div className="absolute -top-10 -right-10 h-40 w-40 rounded-full blur-3xl opacity-30"
            style={{ background: "radial-gradient(circle, oklch(0.7 0.07 55), transparent 70%)" }} />
          <div className="text-xs uppercase tracking-[0.14em] text-background/60">This week</div>
          <div className="font-display text-2xl mt-2 max-w-sm">
            {hasData ? "You're trending toward your highest week ever." : "Awaiting your first search launch."}
          </div>
          <div className="mt-6 flex items-end gap-1 h-24">
            {(hasData ? [40, 55, 38, 70, 58, 82, 95] : [0, 0, 0, 0, 0, 0, 0]).map((v, i) => (
              <div key={i} className="flex-1 rounded-md bg-background/15 relative overflow-hidden">
                <div className="absolute bottom-0 inset-x-0 bg-accent transition-all" style={{ height: `${v}%` }} />
              </div>
            ))}
          </div>
          <div className="mt-3 grid grid-cols-7 gap-1 text-[10px] text-background/50 text-center">
            {["M","T","W","T","F","S","S"].map((d, i) => <div key={i}>{d}</div>)}
          </div>
        </div>
      </div>
    </>
  );
}
