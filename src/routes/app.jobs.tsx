"use client";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Filter, MapPin, BookmarkPlus, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { PageHeader } from "@/components/shell/sidebar";
import { Stagger, StaggerItem, HoverLift } from "@/components/motion/primitives";
import { JOBS } from "@/lib/mock/jobs";
import type { Job } from "@/lib/types";

export const Route = createFileRoute("/app/jobs")({
  head: () => ({
    meta: [
      { title: "Job Search — Aria" },
      { name: "description", content: "Search and filter AI-curated jobs from across the web." },
    ],
  }),
  component: JobsPage,
});

function JobCard({ job }: { job: Job }) {
  return (
    <HoverLift>
      <Link
        to="/app/jobs/$jobId"
        params={{ jobId: job.id }}
        className="block rounded-2xl border border-border bg-card p-5 shadow-soft hover:shadow-elegant transition-shadow"
      >
        <div className="flex items-start gap-4">
          <div className="h-12 w-12 rounded-xl bg-foreground text-background flex items-center justify-center font-display text-lg flex-shrink-0">
            {job.companyLogo}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-xs text-muted-foreground">{job.company} · {job.postedAt}</div>
                <div className="font-display text-lg leading-tight mt-0.5">{job.title}</div>
              </div>
              <div className="flex items-center gap-1.5 flex-shrink-0">
                <div className="relative h-12 w-12">
                  <svg viewBox="0 0 48 48" className="h-full w-full -rotate-90">
                    <circle cx="24" cy="24" r="20" stroke="oklch(0.91 0.012 75)" strokeWidth="3" fill="none" />
                    <circle cx="24" cy="24" r="20" stroke="oklch(0.62 0.07 55)" strokeWidth="3" strokeLinecap="round" fill="none"
                      strokeDasharray={2 * Math.PI * 20} strokeDashoffset={2 * Math.PI * 20 * (1 - job.match / 100)} />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center text-xs font-medium">{job.match}</div>
                </div>
              </div>
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1"><MapPin className="h-3 w-3" />{job.location}</span>
              <span>{job.remote}</span>
              <span>{job.salary}</span>
              <span>{job.experience}</span>
            </div>

            <div className="mt-3 flex flex-wrap gap-1.5">
              {job.skills.slice(0, 5).map((s) => (
                <span key={s} className="text-[11px] px-2 py-0.5 rounded-md bg-muted text-muted-foreground">{s}</span>
              ))}
            </div>

            <div className="mt-4 flex items-start gap-2 text-xs text-foreground/80 bg-muted/50 rounded-lg p-3">
              <Sparkles className="h-3.5 w-3.5 text-accent flex-shrink-0 mt-0.5" />
              <span>{job.aiRecommendation}</span>
            </div>

            <div className="mt-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <button onClick={(e) => e.preventDefault()} className="text-xs rounded-full bg-foreground text-background px-3 py-1.5 hover:opacity-90">Apply</button>
                <button onClick={(e) => e.preventDefault()} className="text-xs rounded-full border border-border px-3 py-1.5 hover:bg-muted">Details</button>
              </div>
              <button onClick={(e) => e.preventDefault()} className="h-8 w-8 inline-flex items-center justify-center rounded-full hover:bg-muted text-muted-foreground">
                <BookmarkPlus className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </Link>
    </HoverLift>
  );
}

const REMOTE_OPTIONS = ["Remote", "Hybrid", "Onsite"] as const;
const EXP_OPTIONS = ["Entry", "Mid", "Senior", "Staff", "Principal"] as const;

function JobsPage() {
  const [q, setQ] = useState("");
  const [remote, setRemote] = useState<string[]>([]);
  const [exp, setExp] = useState<string[]>([]);

  const filtered = useMemo(() => {
    return JOBS.filter((j) => {
      if (q && !`${j.title} ${j.company} ${j.skills.join(" ")}`.toLowerCase().includes(q.toLowerCase())) return false;
      if (remote.length && !remote.includes(j.remote)) return false;
      if (exp.length && !exp.includes(j.experience)) return false;
      return true;
    });
  }, [q, remote, exp]);

  const toggle = (arr: string[], v: string, set: (a: string[]) => void) =>
    set(arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);

  return (
    <>
      <PageHeader title="Job Search" subtitle={`${filtered.length} curated roles from the past 24 hours.`} />

      <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-6">
        <aside className="space-y-5">
          <div className="rounded-2xl border border-border bg-card p-4 shadow-soft">
            <div className="flex items-center gap-2 text-xs uppercase tracking-[0.14em] text-muted-foreground mb-3">
              <Filter className="h-3.5 w-3.5" /> Filters
            </div>
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Role, company, skill"
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent"
            />

            <div className="mt-5">
              <div className="text-xs font-medium mb-2">Work mode</div>
              <div className="flex flex-wrap gap-1.5">
                {REMOTE_OPTIONS.map((o) => (
                  <button key={o} onClick={() => toggle(remote, o, setRemote)}
                    className={`text-xs px-2.5 py-1 rounded-full border transition ${remote.includes(o) ? "bg-foreground text-background border-foreground" : "border-border hover:bg-muted"}`}>
                    {o}
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-5">
              <div className="text-xs font-medium mb-2">Experience</div>
              <div className="flex flex-wrap gap-1.5">
                {EXP_OPTIONS.map((o) => (
                  <button key={o} onClick={() => toggle(exp, o, setExp)}
                    className={`text-xs px-2.5 py-1 rounded-full border transition ${exp.includes(o) ? "bg-foreground text-background border-foreground" : "border-border hover:bg-muted"}`}>
                    {o}
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-5">
              <div className="text-xs font-medium mb-2">Salary</div>
              <input type="range" min="80" max="400" defaultValue="180" className="w-full accent-accent" />
              <div className="flex justify-between text-[11px] text-muted-foreground mt-1">
                <span>$80k</span><span>$400k+</span>
              </div>
            </div>
          </div>

          <div className="rounded-2xl bg-foreground text-background p-4 text-xs">
            <div className="font-display text-sm mb-1">Aria's pick today</div>
            <p className="text-background/70">Senior Product Designer at Linear · 96% match</p>
            <motion.div initial={{ width: 0 }} whileInView={{ width: "96%" }} viewport={{ once: true }} transition={{ duration: 1.2 }} className="mt-3 h-1 rounded-full bg-accent" />
          </div>
        </aside>

        <Stagger className="space-y-3">
          {filtered.map((j) => (
            <StaggerItem key={j.id}><JobCard job={j} /></StaggerItem>
          ))}
          {filtered.length === 0 && (
            <div className="rounded-2xl border border-dashed border-border bg-card p-12 text-center text-muted-foreground">
              <div className="font-display text-lg text-foreground">No matches yet</div>
              <p className="text-sm mt-1">Try removing a filter or widening your salary range.</p>
            </div>
          )}
        </Stagger>
      </div>
    </>
  );
}
