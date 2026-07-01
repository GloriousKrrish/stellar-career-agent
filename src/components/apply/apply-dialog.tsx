"use client";
import { motion, AnimatePresence } from "framer-motion";
import { X, Sparkles, Loader2, CheckCircle2, FileText, Mail, User2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useRouter } from "@tanstack/react-router";
import type { Job } from "@/lib/types";
import { getCurrentUser } from "@/lib/auth";
import { api } from "@/lib/api";

type Phase = "drafting" | "ready" | "submitting" | "done";

export function ApplyDialog({
  job,
  runId,
  onClose,
}: {
  job: Job | null;
  runId: string | null;
  onClose: () => void;
}) {
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>("drafting");
  const [note, setNote] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const user = getCurrentUser() || {
    name: "Job Seeker",
    email: "",
    title: "Software Engineer",
    location: "Remote",
    skills: ["TypeScript", "React", "Node"]
  };

  useEffect(() => {
    if (!job) return;
    setPhase("drafting");
    setNote("");
    setErrorMsg("");
    const t = setTimeout(() => setPhase("ready"), 1400);
    return () => clearTimeout(t);
  }, [job]);

  const summary = job
    ? `Aria drafted a tailored application for ${job.title} at ${job.company}. We aligned your ${(user.skills || []).slice(0, 3).join(", ") || "software development"} experience with their ${(job.skills || []).slice(0, 2).join(" and ") || "role"} requirements, and emphasized your work shipping consumer-grade product.`
    : "";

  const coverPreview = job
    ? `Hi ${job.company} team,\n\nI'm reaching out for the ${job.title} role. Over the last few years I've shipped ${(user.skills || []).slice(0, 2).join(" + ") || "software development"} work at the bar your team seems to demand. Three highlights:\n\n· Led a 0→1 surface that drove measurable retention wins.\n· Partnered cross-functionally weekly.\n· Mentored team members while staying hands-on in the codebase.\n\nI'd love to talk. — ${user.name}`
    : "";

  const handleSubmit = async () => {
    if (!job) return;
    setPhase("submitting");
    setErrorMsg("");
    try {
      const activeRunId = runId || localStorage.getItem("aria.active_run_id") || "manual_enqueue";
      const payload = {
        run_id: activeRunId,
        job_id: job.id,
        job_title: job.title,
        job_company: job.company,
        job_url: job.url || "",
        job_source: job.source || "Web",
      };
      console.log("Sending apply payload:", payload);
      
      // Save active run ID to localStorage and fire custom event to wake up WebSocket stream
      localStorage.setItem("aria.active_run_id", activeRunId);
      window.dispatchEvent(new CustomEvent("aria:run_started", { detail: activeRunId }));
      
      await api.enqueueForAutoApply(payload);
      
      // Invalidate active router layout to instantly reload Applications Board data
      router.invalidate();
      
      setPhase("done");
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || "Failed to enqueue application.");
      setPhase("ready");
    }
  };

  return (
    <AnimatePresence>
      {job && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 z-50 bg-foreground/40 backdrop-blur-sm flex items-center justify-center p-4"
        >
          <motion.div
            initial={{ y: 16, opacity: 0, scale: 0.98 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            exit={{ y: 16, opacity: 0, scale: 0.98 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-2xl bg-card border border-border rounded-3xl shadow-glow overflow-hidden max-h-[90vh] flex flex-col"
          >
            <header className="px-6 py-4 border-b border-border flex items-start justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-xl bg-foreground text-background flex items-center justify-center font-display">
                  {job.companyLogo}
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">{job.company} · {job.location}</div>
                  <h3 className="font-display text-lg">{job.title}</h3>
                </div>
              </div>
              <button onClick={onClose} className="h-8 w-8 inline-flex items-center justify-center rounded-md hover:bg-muted">
                <X className="h-4 w-4" />
              </button>
            </header>

            <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
              {phase === "drafting" && (
                <div className="py-10 text-center">
                  <div className="inline-flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin text-accent" />
                    Aria is drafting your application...
                  </div>
                  <div className="mt-4 text-xs text-muted-foreground space-y-1">
                    <div>· Parsing job description</div>
                    <div>· Mapping your resume to requirements</div>
                    <div>· Generating tailored cover letter</div>
                  </div>
                </div>
              )}

              {phase === "ready" && (
                <>
                  <div className="rounded-2xl bg-muted/50 p-4 flex items-start gap-2.5">
                    <Sparkles className="h-4 w-4 text-accent flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-foreground/85 leading-relaxed">{summary}</p>
                  </div>

                  {errorMsg && (
                    <div className="rounded-2xl bg-red-500/10 border border-red-500/20 p-4 text-sm text-red-500">
                      {errorMsg}
                    </div>
                  )}

                  <Section icon={<User2 className="h-3.5 w-3.5" />} title="Your profile">
                    <Row label="Name" value={user.name} />
                    <Row label="Email" value={user.email} />
                    <Row label="Location" value={user.location || "Remote"} />
                  </Section>

                  <Section icon={<FileText className="h-3.5 w-3.5" />} title="Resume">
                    <div className="text-sm">
                      {user.name ? `${user.name.toLowerCase().replace(/\s+/g, '_')}_resume.pdf` : 'resume.pdf'}
                      <span className="text-xs text-muted-foreground">· tailored snippet attached</span>
                    </div>
                  </Section>

                  <Section icon={<Mail className="h-3.5 w-3.5" />} title="Cover letter preview">
                    <pre className="text-xs leading-relaxed text-foreground/80 whitespace-pre-wrap font-sans bg-muted/40 rounded-xl p-3 max-h-40 overflow-y-auto">
                      {coverPreview}
                    </pre>
                  </Section>

                  <div>
                    <label className="text-xs font-medium text-muted-foreground">Add a personal note (optional)</label>
                    <textarea
                      value={note}
                      onChange={(e) => setNote(e.target.value)}
                      rows={2}
                      placeholder="One sentence to the hiring manager..."
                      className="mt-1.5 w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 transition resize-none"
                    />
                  </div>
                </>
              )}

              {phase === "submitting" && (
                <div className="py-12 text-center">
                  <Loader2 className="h-6 w-6 animate-spin text-accent mx-auto" />
                  <div className="mt-3 text-sm text-muted-foreground">Queuing application with the AutoApply coordinator...</div>
                </div>
              )}

              {phase === "done" && (
                <div className="py-10 text-center">
                  <div className="mx-auto h-12 w-12 rounded-2xl bg-accent/15 text-accent flex items-center justify-center">
                    <CheckCircle2 className="h-6 w-6" />
                  </div>
                  <h4 className="mt-4 font-display text-xl">Queued for Auto-Apply</h4>
                  <p className="mt-1 text-sm text-muted-foreground">
                    The AutoApply Agent will process this application in the background. You can monitor the progress inside the AI Agents pipeline.
                  </p>
                </div>
              )}
            </div>

            <footer className="px-6 py-4 border-t border-border flex items-center justify-between gap-3 bg-muted/30">
              <button onClick={onClose} className="text-sm text-muted-foreground hover:text-foreground">
                {phase === "done" ? "Close" : "Cancel"}
              </button>
              {phase === "ready" && (
                <button
                  onClick={handleSubmit}
                  className="inline-flex items-center gap-1.5 rounded-full bg-foreground text-background px-5 py-2 text-sm font-medium hover:opacity-90"
                >
                  Confirm & submit
                </button>
              )}
              {phase === "done" && (
                <button
                  onClick={onClose}
                  className="rounded-full bg-foreground text-background px-5 py-2 text-sm font-medium hover:opacity-90"
                >
                  Done
                </button>
              )}
            </footer>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function Section({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-[0.14em] text-muted-foreground mb-2">
        {icon} {title}
      </div>
      <div className="rounded-xl border border-border p-3">{children}</div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3 text-sm py-1">
      <span className="text-muted-foreground text-xs">{label}</span>
      <span>{value}</span>
    </div>
  );
}
