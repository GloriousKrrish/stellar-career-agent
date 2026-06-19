"use client";
import { motion, AnimatePresence } from "framer-motion";
import { X, Sparkles, Loader2, CheckCircle2, FileText, Mail, User2, AlertTriangle, ExternalLink } from "lucide-react";
import { useEffect, useState } from "react";
import { getMe, applyToJob, createOrUpdateApplication, API_BASE } from "@/lib/api";

type Phase = "drafting" | "ready" | "submitting" | "action_required" | "done";

export function ApplyDialog({ job, runId, onClose }: { job: any | null; runId: string; onClose: () => void }) {
  const [phase, setPhase] = useState<Phase>("drafting");
  const [note, setNote] = useState("");
  const [user, setUser] = useState<any>(null);
  const [actionRequired, setActionRequired] = useState<{
    reason: string;
    url: string;
    screenshot: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadUser() {
      try {
        const u = await getMe();
        setUser(u);
      } catch (_) {}
    }
    if (job) {
      loadUser();
      setPhase("drafting");
      setNote("");
      setError(null);
      setActionRequired(null);
      const t = setTimeout(() => setPhase("ready"), 800);
      return () => clearTimeout(t);
    }
  }, [job]);

  const summary = job && user
    ? `Aria drafted a tailored application for ${job.title} at ${job.company}. We aligned your ${(user.skills || []).slice(0, 3).join(", ")} experience with their ${(job.skills || []).slice(0, 2).join(" and ")} requirements, and emphasized your work shipping consumer-grade product.`
    : "";

  const coverPreview = job && user
    ? `Hi ${job.company} team,\n\nI'm reaching out for the ${job.title} role. Over the last few years I've shipped ${(user.skills || []).slice(0, 2).join(" + ")} work at the bar your team seems to demand. Three highlights:\n\n· Led a 0→1 surface that drove measurable retention wins.\n· Partnered cross-functionally with engineering, design and PM weekly.\n· Mentored a small team while staying hands-on in the codebase.\n\nI'd love to talk. — ${user.name}`
    : "";

  const handleSubmit = async () => {
    setPhase("submitting");
    setError(null);
    try {
      const res = await applyToJob(runId, job.id);
      
      if (res.status === "ACTION_REQUIRED" || res.status === "action_required") {
        setActionRequired({
          reason: res.reason || "CAPTCHA or Bot Check encountered",
          url: res.url || job.url,
          screenshot: res.screenshot || "",
        });
        setPhase("action_required");
      } else {
        // Successfully submitted! Save application as Applied
        await createOrUpdateApplication({
          job_id: job.id,
          title: job.title,
          company: job.company,
          stage: "Applied",
          location: job.location,
          salary: job.salary,
          url: job.url,
        });
        setPhase("done");
      }
    } catch (err: any) {
      setError(err.message || "Failed to submit application");
      setPhase("ready");
    }
  };

  const handleMarkAsApplied = async () => {
    try {
      await createOrUpdateApplication({
        job_id: job.id,
        title: job.title,
        company: job.company,
        stage: "Applied",
        location: job.location,
        salary: job.salary,
        url: job.url,
      });
      setPhase("done");
    } catch (err: any) {
      setError(err.message || "Failed to save application");
    }
  };

  const handleSaveDraft = async () => {
    try {
      await createOrUpdateApplication({
        job_id: job.id,
        title: job.title,
        company: job.company,
        stage: "Saved",
        location: job.location,
        salary: job.salary,
        url: job.url,
      });
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to save application");
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
                <div className="h-10 w-10 rounded-xl bg-foreground text-background flex items-center justify-center font-display text-lg">
                  {job.company?.[0]?.toUpperCase() || "?"}
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">{job.company} · {job.location || "Remote"}</div>
                  <h3 className="font-display text-lg">{job.title}</h3>
                </div>
              </div>
              <button onClick={onClose} className="h-8 w-8 inline-flex items-center justify-center rounded-md hover:bg-muted">
                <X className="h-4 w-4" />
              </button>
            </header>

            <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
              {error && (
                <div className="p-3 text-xs rounded-xl bg-red-50 dark:bg-red-950/20 text-red-500 border border-red-200 dark:border-red-900/30">
                  {error}
                </div>
              )}

              {phase === "drafting" && (
                <div className="py-10 text-center">
                  <div className="inline-flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin text-accent" />
                    Aria is tailoring your application...
                  </div>
                  <div className="mt-4 text-xs text-muted-foreground space-y-1">
                    <div>· Mapping resume to requirements</div>
                    <div>· Building AI-aligned bio snippet</div>
                    <div>· Drafting personalized cover letter</div>
                  </div>
                </div>
              )}

              {phase === "ready" && (
                <>
                  <div className="rounded-2xl bg-muted/50 p-4 flex items-start gap-2.5">
                    <Sparkles className="h-4 w-4 text-accent flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-foreground/85 leading-relaxed">{summary}</p>
                  </div>

                  <Section icon={<User2 className="h-3.5 w-3.5" />} title="Your profile">
                    <Row label="Name" value={user?.name || "Loading..."} />
                    <Row label="Email" value={user?.email || ""} />
                    <Row label="Location" value={user?.location || "Remote"} />
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
                <div className="py-12 text-center space-y-3">
                  <Loader2 className="h-6 w-6 animate-spin text-accent mx-auto" />
                  <div className="text-sm font-medium text-foreground">Launching browser application agent...</div>
                  <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                    Aria is filling the job application on the target site. This might require solving security challenges.
                  </p>
                </div>
              )}

              {phase === "action_required" && actionRequired && (
                <div className="space-y-4">
                  <div className="rounded-2xl bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/30 p-4 flex items-start gap-3">
                    <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-sm font-semibold text-foreground">Verification Required</h4>
                      <p className="text-xs text-muted-foreground mt-1">
                        A security check (CAPTCHA, OTP, or email validation) has paused auto-apply.
                      </p>
                      <div className="text-xs text-foreground font-medium mt-2 bg-amber-100/30 p-2 rounded-lg">
                        Reason: {actionRequired.reason}
                      </div>
                    </div>
                  </div>

                  {actionRequired.screenshot && (
                    <div>
                      <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5">Last browser screenshot</div>
                      <div className="rounded-xl border border-border overflow-hidden bg-muted">
                        <img
                          src={actionRequired.screenshot.startsWith("http") || actionRequired.screenshot.startsWith("data:") ? actionRequired.screenshot : `${API_BASE}/${actionRequired.screenshot}`}
                          alt="Bot challenge screenshot"
                          className="w-full max-h-60 object-contain"
                        />
                      </div>
                    </div>
                  )}

                  <div className="flex flex-col gap-2 pt-2">
                    <a
                      href={actionRequired.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="w-full rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-medium py-3 text-sm flex items-center justify-center gap-2 transition"
                    >
                      Complete in New Tab <ExternalLink className="h-4 w-4" />
                    </a>
                    <button
                      onClick={handleMarkAsApplied}
                      className="w-full rounded-xl bg-muted hover:bg-muted/80 text-foreground py-2.5 text-xs font-medium transition"
                    >
                      I submitted this manually, mark as Applied
                    </button>
                  </div>
                </div>
              )}

              {phase === "done" && (
                <div className="py-10 text-center">
                  <div className="mx-auto h-12 w-12 rounded-2xl bg-accent/15 text-accent flex items-center justify-center">
                    <CheckCircle2 className="h-6 w-6" />
                  </div>
                  <h4 className="mt-4 font-display text-xl">Application filed</h4>
                  <p className="mt-1 text-sm text-muted-foreground">
                    This job has been saved to your applications board under the "Applied" column.
                  </p>
                </div>
              )}
            </div>

            <footer className="px-6 py-4 border-t border-border flex items-center justify-between gap-3 bg-muted/30">
              <button onClick={onClose} className="text-sm text-muted-foreground hover:text-foreground">
                {phase === "done" ? "Close" : "Cancel"}
              </button>
              
              <div className="flex gap-2">
                {phase === "ready" && (
                  <>
                    <button
                      onClick={handleSaveDraft}
                      className="rounded-full border border-border px-4 py-2 text-sm font-medium hover:bg-muted transition"
                    >
                      Save to board
                    </button>
                    <button
                      onClick={handleSubmit}
                      className="inline-flex items-center gap-1.5 rounded-full bg-foreground text-background px-5 py-2 text-sm font-medium hover:opacity-90 transition"
                    >
                      Confirm & submit
                    </button>
                  </>
                )}
                {phase === "done" && (
                  <button
                    onClick={onClose}
                    className="rounded-full bg-foreground text-background px-5 py-2 text-sm font-medium hover:opacity-90"
                  >
                    Done
                  </button>
                )}
              </div>
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
      <div className="rounded-xl border border-border p-3 bg-card">{children}</div>
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
