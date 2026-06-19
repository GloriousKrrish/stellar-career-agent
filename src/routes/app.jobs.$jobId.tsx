"use client";
import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { ArrowLeft, MapPin, Building2, Sparkles, BookmarkPlus, Share2 } from "lucide-react";
import { motion } from "framer-motion";
import { useState } from "react";
import { getJob } from "@/lib/mock/jobs";
import type { Job } from "@/lib/types";
import { USER } from "@/lib/mock/user";
import { ApplyDialog } from "@/components/apply/apply-dialog";

export const Route = createFileRoute("/app/jobs/$jobId")({
  loader: ({ params }) => {
    const job = getJob(params.jobId);
    if (!job) throw notFound();
    return { job };
  },
  head: ({ loaderData }) => ({
    meta: [
      { title: `${loaderData?.job.title} · ${loaderData?.job.company} — Aria` },
      { name: "description", content: loaderData?.job.aiRecommendation ?? "" },
    ],
  }),
  notFoundComponent: () => (
    <div className="text-center py-20">
      <div className="font-display text-2xl">Job not found</div>
      <Link to="/app/jobs" className="text-sm text-accent mt-2 inline-block">Back to search</Link>
    </div>
  ),
  component: JobDetail,
});

function JobDetail() {
  const { job } = Route.useLoaderData() as { job: Job };
  const userSet = new Set(USER.skills.map((s) => s.toLowerCase()));
  const [applyOpen, setApplyOpen] = useState(false);

  return (
    <>
      <Link to="/app/jobs" className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mb-6">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to search
      </Link>

      <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-8">
        <article className="space-y-8">
          <header className="flex items-start gap-5">
            <div className="h-16 w-16 rounded-2xl bg-foreground text-background flex items-center justify-center font-display text-2xl">
              {job.companyLogo}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm text-muted-foreground">{job.company}</div>
              <h1 className="font-display text-3xl tracking-tight mt-0.5">{job.title}</h1>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1"><MapPin className="h-3 w-3" />{job.location}</span>
                <span>{job.remote}</span>
                <span>{job.salary}</span>
                <span>Posted {job.postedAt}</span>
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <button onClick={() => setApplyOpen(true)} className="rounded-full bg-foreground text-background px-4 py-2 text-sm font-medium hover:opacity-90">Apply via Aria</button>
              <div className="flex gap-2 justify-end">
                <button className="h-8 w-8 inline-flex items-center justify-center rounded-full border border-border hover:bg-muted"><BookmarkPlus className="h-4 w-4" /></button>
                <button className="h-8 w-8 inline-flex items-center justify-center rounded-full border border-border hover:bg-muted"><Share2 className="h-4 w-4" /></button>
              </div>
            </div>
          </header>

          <section>
            <h2 className="font-display text-xl mb-3">About the role</h2>
            <p className="text-foreground/80 leading-relaxed">{job.description}</p>
          </section>

          <section>
            <h2 className="font-display text-xl mb-3">Responsibilities</h2>
            <ul className="space-y-2 text-sm">
              {job.responsibilities.map((r) => (
                <li key={r} className="flex items-start gap-3">
                  <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-accent flex-shrink-0" /> {r}
                </li>
              ))}
            </ul>
          </section>

          <section>
            <h2 className="font-display text-xl mb-3">Requirements</h2>
            <ul className="space-y-2 text-sm">
              {job.requirements.map((r) => (
                <li key={r} className="flex items-start gap-3">
                  <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-foreground flex-shrink-0" /> {r}
                </li>
              ))}
            </ul>
          </section>

          <section>
            <h2 className="font-display text-xl mb-3">Nice to have</h2>
            <ul className="space-y-2 text-sm text-muted-foreground">
              {job.niceToHave.map((r) => (
                <li key={r} className="flex items-start gap-3">
                  <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-secondary flex-shrink-0" /> {r}
                </li>
              ))}
            </ul>
          </section>

          <section>
            <h2 className="font-display text-xl mb-3">Benefits</h2>
            <div className="flex flex-wrap gap-2">
              {job.benefits.map((b) => (
                <span key={b} className="text-xs px-3 py-1.5 rounded-full bg-muted">{b}</span>
              ))}
            </div>
          </section>
        </article>

        <aside className="space-y-4 lg:sticky lg:top-24 self-start">
          <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Match score</div>
                <div className="font-display text-4xl mt-1 text-accent">{job.match}%</div>
              </div>
              <div className="relative h-20 w-20">
                <svg viewBox="0 0 80 80" className="h-full w-full -rotate-90">
                  <circle cx="40" cy="40" r="34" stroke="oklch(0.91 0.012 75)" strokeWidth="6" fill="none" />
                  <circle cx="40" cy="40" r="34" stroke="oklch(0.62 0.07 55)" strokeWidth="6" strokeLinecap="round" fill="none"
                    strokeDasharray={2 * Math.PI * 34}
                    strokeDashoffset={2 * Math.PI * 34 * (1 - job.match / 100)} />
                </svg>
              </div>
            </div>
            <div className="flex items-start gap-2 text-sm bg-muted/50 rounded-xl p-3">
              <Sparkles className="h-4 w-4 text-accent flex-shrink-0 mt-0.5" />
              <span className="text-foreground/80">{job.aiRecommendation}</span>
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
            <div className="text-xs uppercase tracking-[0.14em] text-muted-foreground mb-4">Skills comparison</div>
            <div className="space-y-3">
              {job.skills.map((s, i) => {
                const have = userSet.has(s.toLowerCase());
                return (
                  <div key={s}>
                    <div className="flex justify-between text-xs mb-1">
                      <span>{s}</span>
                      <span className={have ? "text-accent" : "text-muted-foreground"}>
                        {have ? "You have this" : "Worth adding"}
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: have ? "92%" : "32%" }}
                        transition={{ duration: 1, delay: i * 0.05, ease: [0.22, 1, 0.36, 1] }}
                        className={`h-full ${have ? "bg-accent" : "bg-secondary"}`}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
            <div className="text-xs uppercase tracking-[0.14em] text-muted-foreground mb-3">Salary insight</div>
            <div className="font-display text-2xl">{job.salary}</div>
            <p className="text-xs text-muted-foreground mt-1">12% above market for similar roles in {job.location}.</p>
            <div className="mt-4 h-2 rounded-full bg-muted relative">
              <div className="absolute inset-y-0 left-[20%] right-[15%] rounded-full bg-accent/30" />
              <div className="absolute top-1/2 left-[45%] -translate-y-1/2 h-3 w-3 rounded-full bg-foreground border-2 border-background" />
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
            <div className="flex items-center gap-2 text-xs uppercase tracking-[0.14em] text-muted-foreground mb-3">
              <Building2 className="h-3.5 w-3.5" /> {job.company}
            </div>
            <p className="text-sm text-foreground/80">{job.company} is a leader in {job.industry.toLowerCase()}, headquartered in {job.location}. Known for craft and a high bar.</p>
          </div>
        </aside>
      </div>
      <ApplyDialog job={applyOpen ? job : null} onClose={() => setApplyOpen(false)} />
    </>
  );
}
