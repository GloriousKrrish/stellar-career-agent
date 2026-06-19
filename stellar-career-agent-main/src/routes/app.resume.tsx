"use client";
import { createFileRoute } from "@tanstack/react-router";
import { Upload, FileText, CheckCircle2, Download, Loader2 } from "lucide-react";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PageHeader } from "@/components/shell/sidebar";
import { exportResumeReport } from "@/lib/pdf/resume-report";
import { getMe, uploadResume } from "@/lib/api";

export const Route = createFileRoute("/app/resume")({
  head: () => ({
    meta: [
      { title: "Resume Analyzer — Aria" },
      { name: "description", content: "AI-powered resume strength and ATS scoring." },
    ],
  }),
  component: ResumePage,
});

const steps = ["Reading file", "Parsing structure", "Extracting skills", "Scoring ATS", "Compiling report"];

function Ring({ value, size = 120, label, sub }: { value: number; size?: number; label: string; sub: string }) {
  const r = size / 2 - 10;
  const c = 2 * Math.PI * r;
  return (
    <div className="flex items-center gap-4">
      <div className="relative" style={{ width: size, height: size }}>
        <svg viewBox={`0 0 ${size} ${size}`} className="-rotate-90 w-full h-full">
          <circle cx={size / 2} cy={size / 2} r={r} stroke="oklch(0.91 0.012 75)" strokeWidth="8" fill="none" />
          <motion.circle
            cx={size / 2} cy={size / 2} r={r} stroke="oklch(0.62 0.07 55)" strokeWidth="8" strokeLinecap="round" fill="none"
            strokeDasharray={c}
            initial={{ strokeDashoffset: c }}
            animate={{ strokeDashoffset: c * (1 - value / 100) }}
            transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1] }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center font-display text-2xl">{value}</div>
      </div>
      <div>
        <div className="font-display">{label}</div>
        <div className="text-xs text-muted-foreground">{sub}</div>
      </div>
    </div>
  );
}

function ResumePage() {
  const [user, setUser] = useState<any>(null);
  const [phase, setPhase] = useState<"idle" | "parsing" | "done">("idle");
  const [step, setStep] = useState(0);
  const [fileName, setFileName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadUser() {
      try {
        const u = await getMe();
        setUser(u);
        if (u.resume_score || u.ats_score) {
          setPhase("done");
        }
      } catch (_) {}
      setLoading(false);
    }
    loadUser();
  }, []);

  const handleUpload = async (file: File) => {
    setFileName(file.name);
    setPhase("parsing");
    setStep(1);
    setError(null);
    try {
      setStep(2);
      await uploadResume(file, true);
      setStep(3);
      setStep(4);
      setStep(5);
      const updatedUser = await getMe();
      setUser(updatedUser);
      setPhase("done");
    } catch (err: any) {
      setError(err.message || "Failed to analyze resume");
      setPhase("idle");
    }
  };

  const triggerFileInput = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".pdf,.docx,.txt";
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        handleUpload(file);
      }
    };
    input.click();
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
      <PageHeader
        title="Resume Analyzer"
        subtitle="Upload your resume. Aria does the rest."
        actions={
          phase === "done" && user ? (
            <button
              onClick={() => exportResumeReport(user)}
              className="inline-flex items-center gap-1.5 rounded-full bg-foreground text-background px-4 py-2 text-sm font-medium hover:opacity-90 transition"
            >
              <Download className="h-3.5 w-3.5" /> Export PDF report
            </button>
          ) : undefined
        }
      />

      {error && (
        <div className="mb-4 text-xs text-red-500 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/30 rounded-xl p-3">
          {error}
        </div>
      )}

      <AnimatePresence mode="wait">
        {phase === "idle" && (
          <motion.div key="idle" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.4 }}>
            <div onClick={triggerFileInput}
              className="cursor-pointer rounded-3xl border-2 border-dashed border-border bg-card hover:border-accent hover:bg-muted/40 transition-colors p-16 text-center shadow-soft">
              <div className="mx-auto h-14 w-14 rounded-2xl bg-muted flex items-center justify-center">
                <Upload className="h-6 w-6 text-accent" />
              </div>
              <div className="mt-5 font-display text-xl">Drop your resume here</div>
              <p className="mt-1 text-sm text-muted-foreground">PDF, DOCX or TXT · up to 10MB</p>
              <button className="mt-6 rounded-full bg-foreground text-background px-5 py-2 text-sm">Browse files</button>
            </div>
          </motion.div>
        )}

        {phase === "parsing" && (
          <motion.div key="parsing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="rounded-3xl border border-border bg-card p-10 shadow-soft">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 rounded-xl bg-muted flex items-center justify-center">
                <FileText className="h-5 w-5 text-accent" />
              </div>
              <div>
                <div className="font-display text-lg">{fileName || "resume.pdf"}</div>
                <div className="text-xs text-muted-foreground">Aria is analyzing with Gemini...</div>
              </div>
            </div>
            <div className="mt-8 space-y-3">
              {steps.map((s, i) => (
                <div key={s} className="flex items-center gap-3 text-sm">
                  <div className={`h-5 w-5 rounded-full flex items-center justify-center transition-colors ${i < step ? "bg-accent text-accent-foreground" : "bg-muted text-muted-foreground"}`}>
                    {i < step ? <CheckCircle2 className="h-3 w-3" /> : <span className="h-1.5 w-1.5 rounded-full bg-current" />}
                  </div>
                  <span className={i < step ? "text-foreground" : "text-muted-foreground"}>{s}</span>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {phase === "done" && user && (
          <motion.div key="done" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.5 }} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
                <div className="text-xs uppercase tracking-[0.14em] text-muted-foreground mb-4">Resume strength</div>
                <Ring value={user.resume_score || 0} label="Score rating" sub="Evaluated by Gemini Intelligence" />
              </div>
              <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
                <div className="text-xs uppercase tracking-[0.14em] text-muted-foreground mb-4">ATS compatibility</div>
                <Ring value={user.ats_score || 0} label="ATS scoring" sub="Parses cleanly across common structures" />
              </div>
            </div>

            <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
              <div className="font-display text-lg mb-1">Skills detected</div>
              <p className="text-xs text-muted-foreground mb-4">Aria extracted {(user.skills || []).length} skills from your resume.</p>
              <div className="flex flex-wrap gap-1.5">
                {(user.skills || []).map((s: string) => (
                  <span key={s} className="text-xs px-2.5 py-1 rounded-full bg-muted">{s}</span>
                ))}
                {(user.skills || []).length === 0 && (
                  <span className="text-xs text-muted-foreground">No skills extracted yet</span>
                )}
              </div>
            </div>

            <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
              <div className="font-display text-lg mb-1">Target skills to acquire</div>
              <p className="text-xs text-muted-foreground mb-4">Adding these would maximize match rates on discovered listings.</p>
              <div className="flex flex-wrap gap-1.5">
                {(user.missing_skills || []).map((s: string) => (
                  <span key={s} className="text-xs px-2.5 py-1 rounded-full border border-dashed border-accent text-accent">+ {s}</span>
                ))}
                {(user.missing_skills || []).length === 0 && (
                  <span className="text-xs text-muted-foreground">No skill gaps identified</span>
                )}
              </div>
            </div>

            <div className="rounded-2xl bg-foreground text-background p-6 shadow-soft">
              <div className="font-display text-lg">Quick tips to improve your rating</div>
              <ul className="mt-3 space-y-2 text-sm text-background/80">
                <li>· Quantify impact in your experience using percentages and concrete values.</li>
                <li>· Place skills list section close to the top of the document.</li>
                <li>· Use action verbs (Built, Shipped, Lead) instead of passive explanations.</li>
              </ul>
              <button onClick={() => setPhase("idle")} className="mt-5 rounded-full bg-background/10 hover:bg-background/20 text-sm px-4 py-2 transition">
                Upload another resume
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
