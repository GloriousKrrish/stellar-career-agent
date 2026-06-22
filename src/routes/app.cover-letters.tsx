"use client";
import { createFileRoute } from "@tanstack/react-router";
import { Sparkles, Copy, RefreshCw } from "lucide-react";
import { useState, useEffect } from "react";
import { PageHeader } from "@/components/shell/sidebar";
import { JOBS } from "@/lib/mock/jobs";
import { getCurrentUser } from "@/lib/auth";

export const Route = createFileRoute("/app/cover-letters")({
  head: () => ({
    meta: [
      { title: "Cover Letters — Aria" },
      { name: "description", content: "AI-tailored cover letters for every application." },
    ],
  }),
  component: CoverPage,
});

const SAMPLE = (company: string, role: string, name: string, location: string) => `Dear ${company} team,

I've spent the last six years building product surfaces that millions of people use every day — and what I keep returning to is that the work I'm most proud of looks a lot like what you're building.

The ${role} role is exciting to me because you've struck a rare balance: real craft, real velocity, and a team small enough to feel every decision. I'd love to bring the same energy I poured into shipping our last platform redesign — same restraint, same care for typography, same insistence that the boring screens deserve as much love as the marquee ones.

I'm based in ${location || "India"}, available on three weeks' notice, and would welcome a conversation whenever it suits you.

Warmly,
${name}`;

function CoverPage() {
  const [currentUser, setCurrentUser] = useState<any>(null);

  useEffect(() => {
    setCurrentUser(getCurrentUser());
  }, []);

  const name = currentUser?.name || "Candidate";
  const location = currentUser?.location || "India";

  const [jobId, setJobId] = useState(JOBS[0].id);
  const job = JOBS.find((j) => j.id === jobId)!;
  const [text, setText] = useState("");

  useEffect(() => {
    if (job) {
      setText(SAMPLE(job.company, job.title, name, location));
    }
  }, [jobId, currentUser]);

  const regenerate = () => setText(SAMPLE(job.company, job.title, name, location) + "\n\nPS: I'd love to talk about how I'd approach the first 30 days.");

  return (
    <>
      <PageHeader title="Cover Letters" subtitle="Tailored for every role. Edited by you." />

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6">
        <aside className="space-y-2">
          <div className="text-xs uppercase tracking-[0.14em] text-muted-foreground px-2 mb-1">Roles</div>
          {JOBS.slice(0, 6).map((j) => (
            <button
              key={j.id}
              onClick={() => { setJobId(j.id); }}
              className={`w-full text-left rounded-xl p-3 transition-colors ${j.id === jobId ? "bg-card border border-border shadow-soft" : "hover:bg-muted/60"}`}
            >
              <div className="flex items-center gap-2">
                <div className="h-7 w-7 rounded-lg bg-foreground text-background flex items-center justify-center text-xs font-display">{j.companyLogo}</div>
                <div className="min-w-0 flex-1">
                  <div className="text-xs text-muted-foreground truncate">{j.company}</div>
                  <div className="text-sm truncate">{j.title}</div>
                </div>
              </div>
            </button>
          ))}
        </aside>

        <div className="rounded-2xl border border-border bg-card shadow-soft flex flex-col min-h-[600px]">
          <div className="px-5 py-3 border-b border-border flex items-center justify-between">
            <div>
              <div className="text-xs text-muted-foreground">Drafting for</div>
              <div className="font-display">{job.title} · {job.company}</div>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={regenerate} className="inline-flex items-center gap-1.5 text-xs rounded-full border border-border px-3 py-1.5 hover:bg-muted">
                <RefreshCw className="h-3 w-3" /> Regenerate
              </button>
              <button onClick={() => navigator.clipboard.writeText(text)} className="inline-flex items-center gap-1.5 text-xs rounded-full bg-foreground text-background px-3 py-1.5 hover:opacity-90">
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
            Aria tailored 6 phrases to match {job.company}'s tone of voice.
          </div>
        </div>
      </div>
    </>
  );
}

