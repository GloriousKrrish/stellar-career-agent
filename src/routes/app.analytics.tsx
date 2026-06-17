"use client";
import { createFileRoute } from "@tanstack/react-router";
import { ResponsiveContainer, LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, Tooltip, CartesianGrid, XAxis, YAxis } from "recharts";
import { PageHeader } from "@/components/shell/sidebar";
import { Stagger, StaggerItem } from "@/components/motion/primitives";
import { GROWTH, ROLE_DISTRIBUTION, SALARY_DISTRIBUTION, FUNNEL } from "@/lib/mock/metrics";

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
  return (
    <>
      <PageHeader title="Analytics" subtitle="The shape of your search, at a glance." />
      <Stagger className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <StaggerItem>
          <Card title="Application trend">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={GROWTH} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
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
          <Card title="Interview trend">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={GROWTH} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
                <CartesianGrid stroke="oklch(0.91 0.012 75)" vertical={false} />
                <XAxis dataKey="day" stroke="oklch(0.5 0.012 60)" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis stroke="oklch(0.5 0.012 60)" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: "oklch(1 0 0)", border: "1px solid oklch(0.91 0.012 75)", borderRadius: 12, fontSize: 12 }} />
                <Line type="monotone" dataKey="interviews" stroke={colors[1]} strokeWidth={2.5} dot={{ r: 3, fill: colors[1] }} />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </StaggerItem>

        <StaggerItem>
          <Card title="Role distribution">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={ROLE_DISTRIBUTION} dataKey="value" nameKey="name" innerRadius={48} outerRadius={84} paddingAngle={2}>
                  {ROLE_DISTRIBUTION.map((_, i) => <Cell key={i} fill={colors[i]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: "oklch(1 0 0)", border: "1px solid oklch(0.91 0.012 75)", borderRadius: 12, fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </StaggerItem>

        <StaggerItem>
          <Card title="Salary distribution">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={SALARY_DISTRIBUTION} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
                <CartesianGrid stroke="oklch(0.91 0.012 75)" vertical={false} />
                <XAxis dataKey="band" stroke="oklch(0.5 0.012 60)" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis stroke="oklch(0.5 0.012 60)" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: "oklch(1 0 0)", border: "1px solid oklch(0.91 0.012 75)", borderRadius: 12, fontSize: 12 }} />
                <Bar dataKey="count" fill={colors[0]} radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </StaggerItem>

        <StaggerItem className="lg:col-span-2">
          <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
            <div className="text-xs uppercase tracking-[0.14em] text-muted-foreground mb-5">Pipeline funnel</div>
            <div className="space-y-2.5">
              {FUNNEL.map((row, i) => {
                const pct = (row.value / FUNNEL[0].value) * 100;
                return (
                  <div key={row.stage} className="flex items-center gap-3">
                    <div className="w-24 text-xs text-muted-foreground">{row.stage}</div>
                    <div className="flex-1 h-8 rounded-lg bg-muted relative overflow-hidden">
                      <div className="absolute inset-y-0 left-0 rounded-lg flex items-center justify-end pr-3 text-xs text-background font-medium"
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
    </>
  );
}
