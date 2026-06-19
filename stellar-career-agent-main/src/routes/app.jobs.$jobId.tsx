"use client";
import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { ArrowLeft, MapPin, Building2, Sparkles, BookmarkPlus, Share2, Loader2, Globe } from "lucide-react";
import { motion } from "framer-motion";
import { useState, useEffect } from "react";
import { ApplyDialog } from "@/components/apply/apply-dialog";
import { getMe } from "@/lib/api";

interface JobDetailSearch {
  runId?: string;
}

export const Route = createFileRoute("/app/jobs/$jobId")({
  validateSearch: (search: Record<string, unknown>): JobDetailSearch => {
    return {
      runId: search.runId as string | undefined,
    };
  },
  loader: async ({ params, search }) => {
    const runId = search.runId || (typeof window !== "undefined" ? window.localStorage.getItem("aria.run_id") : null);
    if (!runId) throw notFound();

    const { getWorkflowJobs, explainJobMatch } = await import("@/lib/api");
    const data = await getWorkflowJobs(runId);
    const job = data.jobs?.find((j: any) => j.id === params.jobId);
    if (!job) throw notFound();

    let explanation = "";
    try {
      const expRes = await explainJobMatch(runId, params.jobId);
      explanation = expRes.explanation;
    } catch (_) {}

    return { job, runId, explanation };
  },
  head: ({ loaderData }) => ({
    meta: [
      { title: `${loaderData?.job?.title || "Job Detail"} · ${loaderData?.job?.company || "Company"} — Aria` },
      { name: "description", content: loaderData?.job?.ai_recommendation ?? "" },
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
  const { job, runId, explanation } = Route.useLoaderData() as { job: any; runId: string; explanation: string };
  const [applyOpen, setApplyOpen] = useState(false);
  const [userSkills, setUserSkills] = useState<string[]>([]);

  useEffect(() => {
    async function fetchUser() {
      try {
        const user = await getMe();
        if (user && user.skills) {
          setUserSkills(user.skills);
        }
      } catch (_) {}
    }
    fetchUser();
  }, []);

  const userSet = new Set(userSkills.map((s) => s.toLowerCase()));
  const matchScore = job.overall_match || 0;

  const getSourceDisplay = (src: string) => {
    const s = src.toLowerCase();
    if (s.includes("weworkremotely")) return "WeWorkRemotely";
    if (s.includes("glassdoor")) return "Glassdoor";
    if (s.includes("naukri")) return "Naukri";
    return src || "Web";
  };

  return (
    <>
      <Link to="/app/jobs" className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mb-6">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to search
      </Link>

      <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-8">
        <article className="space-y-8">
          <header className="flex items-start gap-5">
            <div className="h-16 w-16 rounded-2xl bg-foreground text-background flex items-center justify-center font-display text-2xl shrink-0">
              {job.company?.[0]?.toUpperCase() || "?"}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">{job.company}</span>
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-accent/10 text-accent border border-accent/20">
                  <Globe className="h-2.5 w-2.5" /> {getSourceDisplay(job.source)}
                </span>
              </div>
              <h1 className="font-display text-3xl tracking-tight mt-1">{job.title}</h1>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1"><MapPin className="h-3 w-3" />{job.location || "Remote"}</span>
                <span>{job.remote || "Remote"}</span>
                <span>{job.salary || "N/A"}</span>
                <span>Posted {job.posted_at ? new Date(job.posted_at).toLocaleDateString() : "Recently"}</span>
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <button onClick={() => setApplyOpen(true)} className="rounded-full bg-foreground text-background px-4 py-2 text-sm font-medium hover:opacity-90 transition">
                Apply via Aria
              </button>
            </div>
          </header>

          <section>
            <h2 className="font-display text-xl mb-3">About the role</h2>
            <p className="text-foreground/80 leading-relaxed whitespace-pre-line">
              {job.description || "No description provided. Click the original link to apply."}
            </p>
          </section>

          {job.responsibilities && job.responsibilities.length > 0 && (
            <section>
              <h2 className="font-display text-xl mb-3">Responsibilities</h2>
              <ul className="space-y-2 text-sm">
                {job.responsibilities.map((r: string) => (
                  <li key={r} className="flex items-start gap-3">
                    <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-accent flex-shrink-0" /> {r}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {job.requirements && job.requirements.length > 0 && (
            <section>
              <h2 className="font-display text-xl mb-3">Requirements</h2>
              <ul className="space-y-2 text-sm">
                {job.requirements.map((r: string) => (
                  <li key={r} className="flex items-start gap-3">
                    <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-foreground flex-shrink-0" /> {r}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {job.benefits && job.benefits.length > 0 && (
            <section>
              <h2 className="font-display text-xl mb-3">Benefits</h2>
              <div className="flex flex-wrap gap-2">
                {job.benefits.map((b: string) => (
                  <span key={b} className="text-xs px-3 py-1.5 rounded-full bg-muted">{b}</span>
                ))}
              </div>
            </section>
          )}
        </article>

        <aside className="space-y-4 lg:sticky lg:top-24 self-start">
          <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Match score</div>
                <div className="font-display text-4xl mt-1 text-accent">{matchScore}%</div>
              </div>
              <div className="relative h-20 w-20">
                <svg viewBox="0 0 80 80" className="h-full w-full -rotate-90">
                  <circle cx="40" cy="40" r="34" stroke="oklch(0.91 0.012 75)" strokeWidth="6" fill="none" />
                  <circle cx="40" cy="40" r="34" stroke="oklch(0.62 0.07 55)" strokeWidth="6" strokeLinecap="round" fill="none"
                    strokeDasharray={2 * Math.PI * 34}
                    strokeDashoffset={2 * Math.PI * 34 * (1 - matchScore / 100)} />
                </svg>
              </div>
            </div>
            {job.ai_recommendation && (
              <div className="flex items-start gap-2 text-sm bg-muted/50 rounded-xl p-3">
                <Sparkles className="h-4 w-4 text-accent flex-shrink-0 mt-0.5" />
                <span className="text-foreground/80">{job.ai_recommendation}</span>
              </div>
            )}
          </div>

          {explanation && (
            <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
              <div className="text-xs uppercase tracking-[0.14em] text-muted-foreground mb-3">AI Explanation</div>
              <div className="text-sm text-foreground/80 leading-relaxed whitespace-pre-line bg-muted/20 p-4 rounded-xl border border-border/50">
                {explanation}
              </div>
            </div>
          )}

          {job.skills && job.skills.length > 0 && (
            <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
              <div className="text-xs uppercase tracking-[0.14em] text-muted-foreground mb-4">Skills comparison</div>
              <div className="space-y-3">
                {job.skills.map((s: string, i: number) => {
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
          )}

          {job.salary && (
            <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
              <div className="text-xs uppercase tracking-[0.14em] text-muted-foreground mb-3">Salary insight</div>
              <div className="font-display text-2xl">{job.salary}</div>
              <p className="text-xs text-muted-foreground mt-1">Base rate for similar roles in {job.location || "Remote"}.</p>
            </div>
          )}

          <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
            <div className="flex items-center gap-2 text-xs uppercase tracking-[0.14em] text-muted-foreground mb-3">
              <Building2 className="h-3.5 w-3.5" /> {job.company}
            </div>
            <p className="text-sm text-foreground/80">
              Discovered from {getSourceDisplay(job.source)}: {job.title} at {job.company} located in {job.location || "Remote"}.
            </p>
          </div>
        </aside>
      </div>

      <ApplyDialog job={applyOpen ? job : null} runId={runId} onClose={() => setApplyOpen(false)} />
    </>
  );
}
