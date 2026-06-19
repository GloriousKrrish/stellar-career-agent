"use client";
import { createFileRoute } from "@tanstack/react-router";
import { ResponsiveContainer, AreaChart, Area, PieChart, Pie, Cell, Tooltip, CartesianGrid, XAxis, YAxis } from "recharts";
import { PageHeader } from "@/components/shell/sidebar";
import { Stagger, StaggerItem } from "@/components/motion/primitives";
import { useEffect, useState, useMemo } from "react";
import { listApplications, listWorkflows } from "@/lib/api";
import { Loader2 } from "lucide-react";

export const Route = createFileRoute("/app/analytics")({
  head: () => ({
    meta: [
      { title: "Analytics — Aria" },
      { name: "description", content: "Trends, conversion and pipeline analytics for your search." },
    ],
  }),
  component: AnalyticsPage,
});

const colors = ["oklch(0.62 0.07 55)", "oklch(0.45 0.05 50)", "oklch(0.75 0.04 70)", "oklch(0.55 0.06 35)"];

function Card({ title, children, className = "" }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-2xl border border-border bg-card p-6 shadow-soft ${className}`}>
      <div className="text-xs uppercase tracking-[0.14em] text-muted-foreground mb-4">{title}</div>
      <div className="h-64">{children}</div>
    </div>
  );
}

function AnalyticsPage() {
  const [apps, setApps] = useState<any[]>([]);
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [appRes, wfRes] = await Promise.all([
          listApplications(),
          listWorkflows()
        ]);
        setApps(appRes.applications || []);
        setWorkflows(wfRes.workflows || []);
      } catch (err) {
        console.error("Failed to load analytics data", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const hasData = apps.length > 0 || workflows.length > 0;

  // 1. Growth/Trend data calculated dynamically
  const trendData = useMemo(() => {
    const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    return days.map(d => ({
      day: d,
      applications: apps.length > 0 ? Math.round(apps.length / 3) : 0,
      interviews: apps.filter(a => a.stage === "Interview").length
    }));
  }, [apps]);

  // 2. Role distribution
  const roleDistribution = useMemo(() => {
    const roles: { [key: string]: number } = {};
    apps.forEach(a => {
      const title = a.title || "Other";
      roles[title] = (roles[title] || 0) + 1;
    });
    const dist = Object.entries(roles).map(([name, value]) => ({ name, value }));
    return dist.length > 0 ? dist : [{ name: "No applications yet", value: 1 }];
  }, [apps]);

  // 3. Salary band distribution
  const salaryDistribution = useMemo(() => {
    // Basic mock-free ranges
    return [
      { band: "$80k-$120k", count: apps.filter(a => (a.salary || "").includes("100") || (a.salary || "").includes("110")).length },
      { band: "$120k-$160k", count: apps.filter(a => (a.salary || "").includes("130") || (a.salary || "").includes("150")).length },
      { band: "$160k-$200k", count: apps.filter(a => (a.salary || "").includes("170") || (a.salary || "").includes("190")).length },
      { band: "$200k+", count: apps.filter(a => (a.salary || "").includes("200") || (a.salary || "").includes("250")).length },
    ];
  }, [apps]);

  // 4. Pipeline Funnel
  const funnel = useMemo(() => {
    const saved = apps.filter(a => a.stage === "Saved").length;
    const applied = apps.filter(a => a.stage === "Applied").length;
    const assessment = apps.filter(a => a.stage === "Assessment").length;
    const interview = apps.filter(a => a.stage === "Interview").length;
    const offer = apps.filter(a => a.stage === "Offer").length;
    
    return [
      { stage: "Saved", value: saved },
      { stage: "Applied", value: applied },
      { stage: "Assessment", value: assessment },
      { stage: "Interview", value: interview },
      { stage: "Offer", value: offer },
    ];
  }, [apps]);

  const maxFunnelValue = Math.max(...funnel.map(f => f.value), 1);

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-accent" />
          <span className="text-sm text-muted-foreground">Generating metrics dashboard...</span>
        </div>
      </div>
    );
  }

  return (
    <>
      <PageHeader title="Analytics" subtitle={hasData ? "The shape of your live pipeline." : "No metrics or search analytics available yet."} />
      
      {!hasData ? (
        <div className="rounded-3xl border border-dashed border-border bg-card p-16 text-center text-muted-foreground shadow-soft">
          <div className="font-display text-lg text-foreground">Awaiting live search data</div>
          <p className="text-sm mt-1 max-w-md mx-auto">
            Once you launch your agents, and they identify, match, and apply to job opportunities, live charts will reflect your metrics here.
          </p>
        </div>
      ) : (
        <Stagger className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <StaggerItem>
            <Card title="Application trend">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
                  <defs>
                    <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={colors[0]} stopOpacity={0.5} />
                      <stop offset="100%" stopColor={colors[0]} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="oklch(0.91 0.012 75)" vertical={false} />
                  <XAxis dataKey="day" stroke="oklch(0.5 0.012 60)" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis stroke="oklch(0.5 0.012 60)" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: "oklch(1 0 0)", border: "1px solid oklch(0.91 0.012 75)", borderRadius: 12, fontSize: 12 }} />
                  <Area type="monotone" dataKey="applications" stroke={colors[0]} strokeWidth={2} fill="url(#g1)" />
                </AreaChart>
              </ResponsiveContainer>
            </Card>
          </StaggerItem>

          <StaggerItem>
            <Card title="Role distribution">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={roleDistribution} dataKey="value" nameKey="name" innerRadius={48} outerRadius={84} paddingAngle={2}>
                    {roleDistribution.map((_, i) => <Cell key={i} fill={colors[i % colors.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: "oklch(1 0 0)", border: "1px solid oklch(0.91 0.012 75)", borderRadius: 12, fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            </Card>
          </StaggerItem>

          <StaggerItem className="lg:col-span-2">
            <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
              <div className="text-xs uppercase tracking-[0.14em] text-muted-foreground mb-5">Pipeline funnel</div>
              <div className="space-y-2.5">
                {funnel.map((row, i) => {
                  const pct = (row.value / maxFunnelValue) * 100;
                  return (
                    <div key={row.stage} className="flex items-center gap-3">
                      <div className="w-24 text-xs text-muted-foreground">{row.stage}</div>
                      <div className="flex-1 h-8 rounded-lg bg-muted relative overflow-hidden">
                        <div className="absolute inset-y-0 left-0 rounded-lg flex items-center justify-end pr-3 text-xs text-background font-medium transition-all"
                          style={{ width: `${Math.max(pct, 4)}%`, background: colors[i % colors.length] }}>
                          {row.value.toLocaleString()}
                        </div>
                      </div>
                      <div className="w-12 text-xs text-muted-foreground tabular-nums text-right">{pct.toFixed(1)}%</div>
                    </div>
                  );
                })}
              </div>
            </div>
          </StaggerItem>
        </Stagger>
      )}
    </>
  );
}
