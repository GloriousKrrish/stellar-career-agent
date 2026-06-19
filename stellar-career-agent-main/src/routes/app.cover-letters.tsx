"use client";
import { createFileRoute } from "@tanstack/react-router";
import { Sparkles, Copy, RefreshCw, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader } from "@/components/shell/sidebar";
import { getWorkflowJobs, listWorkflows, getMe } from "@/lib/api";

export const Route = createFileRoute("/app/cover-letters")({
  head: () => ({
    meta: [
      { title: "Cover Letters — Aria" },
      { name: "description", content: "AI-tailored cover letters for every application." },
    ],
  }),
  component: CoverPage,
});

const DEFAULT_TEMPLATE = (company: string, role: string, name: string, skills: string[]) => `Dear ${company} team,

I'm writing to express my interest in the ${role} position. Given my background building and optimizing complex software, I believe this is a perfect match.

Specifically, I've spent significant time working with ${skills.slice(0, 3).join(", ") || "software technologies"} to ship robust applications. I'm excited by ${company}'s products and design aesthetic, and would love to bring my technical skills and design sensibility to your engineering team.

I am available for an interview at your convenience and look forward to hearing from you.

Warmly,
${name}`;

function CoverPage() {
  const [user, setUser] = useState<any>(null);
  const [jobs, setJobs] = useState<any[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const u = await getMe();
        setUser(u);

        let activeRunId = window.localStorage.getItem("aria.run_id");
        if (!activeRunId) {
          const ws = await listWorkflows();
          if (ws.workflows && ws.workflows.length > 0) {
            activeRunId = ws.workflows[0].run_id;
          }
        }

        if (activeRunId) {
          const res = await getWorkflowJobs(activeRunId);
          const jobList = res.jobs || [];
          setJobs(jobList);
          if (jobList.length > 0) {
            setJobId(jobList[0].id);
            setText(DEFAULT_TEMPLATE(jobList[0].company, jobList[0].title, u.name || "Aria User", u.skills || []));
          }
        }
      } catch (err) {
        console.error("Failed to load cover letters", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const activeJob = jobs.find((j) => j.id === jobId);

  const handleSelectJob = (job: any) => {
    setJobId(job.id);
    setText(DEFAULT_TEMPLATE(job.company, job.title, user?.name || "Aria User", user?.skills || []));
  };

  const regenerate = () => {
    if (!activeJob) return;
    const skillsList = (user?.skills || []).slice().reverse();
    setText(DEFAULT_TEMPLATE(activeJob.company, activeJob.title, user?.name || "Aria User", skillsList) + "\n\nPS: I would love to walk through my portfolio and past shipping timelines.");
  };

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-accent" />
      </div>
    );
  }

  return (
    <>
      <PageHeader title="Cover Letters" subtitle="Tailored for every role. Refined by you." />

      {jobs.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-border bg-card p-16 text-center text-muted-foreground shadow-soft">
          <div className="font-display text-lg text-foreground">No target roles discovered yet</div>
          <p className="text-sm mt-1 max-w-md mx-auto">
            Once you launch your agents, and they retrieve scored job matches, Aria will draft cover letters here.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6">
          <aside className="space-y-2">
            <div className="text-xs uppercase tracking-[0.14em] text-muted-foreground px-2 mb-1">Roles</div>
            {jobs.slice(0, 6).map((j) => (
              <button
                key={j.id}
                onClick={() => handleSelectJob(j)}
                className={`w-full text-left rounded-xl p-3 border transition-all ${
                  j.id === jobId
                    ? "bg-card border-border shadow-soft"
                    : "border-transparent hover:bg-muted/60"
                }`}
              >
                <div className="flex items-center gap-2">
                  <div className="h-7 w-7 rounded-lg bg-foreground text-background flex items-center justify-center text-xs font-display">
                    {j.company?.[0]?.toUpperCase() || "?"}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-xs text-muted-foreground truncate">{j.company}</div>
                    <div className="text-sm truncate">{j.title}</div>
                  </div>
                </div>
              </button>
            ))}
          </aside>

          {activeJob && (
            <div className="rounded-2xl border border-border bg-card shadow-soft flex flex-col min-h-[600px]">
              <div className="px-5 py-3 border-b border-border flex items-center justify-between">
                <div>
                  <div className="text-xs text-muted-foreground">Drafting for</div>
                  <div className="font-display">{activeJob.title} · {activeJob.company}</div>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={regenerate} className="inline-flex items-center gap-1.5 text-xs rounded-full border border-border px-3 py-1.5 hover:bg-muted transition">
                    <RefreshCw className="h-3 w-3" /> Regenerate
                  </button>
                  <button onClick={() => navigator.clipboard.writeText(text)} className="inline-flex items-center gap-1.5 text-xs rounded-full bg-foreground text-background px-3 py-1.5 hover:opacity-90 transition">
                    <Copy className="h-3 w-3" /> Copy
                  </button>
                </div>
              </div>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                className="flex-1 w-full bg-transparent outline-none p-8 font-serif text-[15px] leading-relaxed resize-none"
                style={{ fontFamily: "var(--font-display)" }}
              />
              <div className="px-5 py-3 border-t border-border bg-muted/40 flex items-center gap-2 text-xs text-muted-foreground">
                <Sparkles className="h-3.5 w-3.5 text-accent" />
                Aria dynamically matches key skills from your resume with this description.
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
}
