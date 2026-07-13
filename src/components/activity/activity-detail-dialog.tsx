"use client";
import { motion, AnimatePresence } from "framer-motion";
import { X, Sparkles, Clock, ArrowRight, CheckCircle2 } from "lucide-react";
import type { ActivityEvent } from "@/lib/types";

const kindLabel: Record<ActivityEvent["kind"], string> = {
  discover: "Discovery",
  match: "Matching",
  apply: "Auto Apply",
  interview: "Interview",
  info: "Info",
};

function buildLog(e: ActivityEvent): { time: string; from: string; to?: string; text: string }[] {
  switch (e.kind) {
    case "discover":
      return [
        { time: "T-0.0s", from: "Scheduler", to: "Discovery", text: "Triggered hourly crawl across 40+ sources." },
        { time: "T-0.3s", from: "Discovery", text: "Issued parallel queries against Wellfound, LinkedIn, Hacker News, Greenhouse, Lever." },
        { time: "T-1.8s", from: "Discovery", text: "Received 312 candidate listings. De-duplicated against existing index (124 already known)." },
        { time: "T-2.1s", from: "Discovery", to: "Matching", text: e.text + ". Forwarded 8 new roles for scoring." },
      ];
    case "match":
      return [
        { time: "T-0.0s", from: "Discovery", to: "Matching", text: "Received role payload + JD embeddings." },
        { time: "T-0.4s", from: "Matching", text: "Computed cosine similarity against your resume vector (0.91)." },
        { time: "T-0.6s", from: "Matching", text: "Applied multi-factor scoring: skills 38pt · seniority 22pt · comp 18pt · location 16pt." },
        { time: "T-0.9s", from: "Matching", to: "User feed", text: e.text + ". Surfaced to dashboard." },
      ];
    case "apply":
      return [
        { time: "T-0.0s", from: "Matching", to: "Auto Apply", text: "Role passed match threshold (>= 88%). Drafting application." },
        { time: "T-1.2s", from: "Auto Apply", text: "Tailored resume bullets to JD. Generated cover letter draft." },
        { time: "T-2.4s", from: "Auto Apply", text: "Validated form fields against company portal schema." },
        { time: "T-2.9s", from: "Auto Apply", to: "Tracking", text: e.text + ". Awaiting user confirmation or auto-submit window." },
      ];
    case "interview":
      return [
        { time: "T-0.0s", from: "Tracking", text: "Inbox sync picked up calendar invite." },
        { time: "T-0.3s", from: "Tracking", to: "Interview", text: "Parsed company, role and round type from email signal." },
        { time: "T-1.1s", from: "Interview", text: e.text + ". Generated 12 likely questions + 3 frameworks." },
      ];
    default:
      return [
        { time: "T-0.0s", from: e.agent, text: e.text },
        { time: "T-0.4s", from: e.agent, text: "Persisted to user activity log." },
      ];
  }
}

export function ActivityDetailDialog({ event, onClose }: { event: ActivityEvent | null; onClose: () => void }) {
  return (
    <AnimatePresence>
      {event && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 z-50 bg-foreground/30 backdrop-blur-sm flex items-stretch justify-end"
        >
          <motion.aside
            initial={{ x: 480 }}
            animate={{ x: 0 }}
            exit={{ x: 480 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-md bg-card border-l border-border h-full overflow-y-auto"
          >
            <header className="sticky top-0 bg-card/95 backdrop-blur border-b border-border px-6 py-4 flex items-start justify-between gap-3 z-10">
              <div>
                <div className="text-[10px] uppercase tracking-[0.16em] text-accent">{kindLabel[event.kind]} agent</div>
                <h3 className="font-display text-lg mt-0.5 leading-tight">{event.text}</h3>
                <div className="text-xs text-muted-foreground mt-1 inline-flex items-center gap-1">
                  <Clock className="h-3 w-3" /> {event.time}
                </div>
              </div>
              <button onClick={onClose} className="h-8 w-8 inline-flex items-center justify-center rounded-md hover:bg-muted">
                <X className="h-4 w-4" />
              </button>
            </header>

            <section className="p-6 space-y-6">
              <div className="rounded-2xl bg-muted/50 p-4">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Sparkles className="h-3.5 w-3.5 text-accent" /> Why this happened
                </div>
                <p className="mt-2 text-sm text-foreground/80 leading-relaxed">
                  This task ran because the {event.agent} agent's policy triggered on a fresh signal in your pipeline.
                  Aria coordinates each agent so signals flow without you intervening.
                </p>
              </div>

              <div>
                <div className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground mb-3">Task-to-task trace</div>
                <ol className="space-y-3">
                  {buildLog(event).map((s, i) => (
                    <li key={i} className="rounded-xl border border-border p-3">
                      <div className="flex items-center justify-between text-[11px] text-muted-foreground tabular-nums">
                        <span>{s.time}</span>
                        <span className="inline-flex items-center gap-1">
                          {s.from}
                          {s.to && <><ArrowRight className="h-3 w-3" /> {s.to}</>}
                        </span>
                      </div>
                      <p className="text-sm mt-1.5 leading-snug">{s.text}</p>
                    </li>
                  ))}
                </ol>
              </div>

              <div>
                <div className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground mb-3">Outcome</div>
                {event.text.toLowerCase().includes("failed") || event.text.toLowerCase().includes("error") ? (
                  <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-3 flex items-start gap-2.5">
                    <X className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-red-500/90">
                      Task failed. See the log above for details and errors encountered during execution.
                    </p>
                  </div>
                ) : event.text.toLowerCase().includes("requires manual") || event.text.toLowerCase().includes("manual review") || event.text.toLowerCase().includes("awaiting") || event.text.toLowerCase().includes("pending") ? (
                  <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 flex items-start gap-2.5">
                    <Clock className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-amber-500/90">
                      Awaiting action. This task is currently paused awaiting user verification or manual intervention.
                    </p>
                  </div>
                ) : (
                  <div className="rounded-xl border border-border p-3 flex items-start gap-2.5">
                    <CheckCircle2 className="h-4 w-4 text-accent flex-shrink-0 mt-0.5" />
                    <p className="text-sm">
                      Task completed cleanly. Signals were forwarded to downstream agents and the activity feed.
                    </p>
                  </div>
                )}
              </div>

              <div className="rounded-2xl bg-foreground text-background p-4">
                <div className="text-xs text-background/70">Ask Aria</div>
                <p className="mt-1 text-sm">"Explain this trace in plain English" or "What should I do next?"</p>
                <button className="mt-3 rounded-lg bg-background/10 hover:bg-background/20 transition px-3 py-1.5 text-xs">
                  Open chat
                </button>
              </div>
            </section>
          </motion.aside>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
