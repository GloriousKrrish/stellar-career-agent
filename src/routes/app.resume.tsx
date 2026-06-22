"use client";
import { createFileRoute } from "@tanstack/react-router";
import { Upload, FileText, CheckCircle2, Download } from "lucide-react";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PageHeader } from "@/components/shell/sidebar";
import { getCurrentUser } from "@/lib/auth";
import { api } from "@/lib/api";
import { exportResumeReport } from "@/lib/pdf/resume-report";

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
  const [phase, setPhase] = useState<"idle" | "parsing" | "done">("idle");
  const [step, setStep] = useState(0);
  const [resumeName, setResumeName] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [userProfile, setUserProfile] = useState<any>(null);

  useEffect(() => {
    // Load initial user details if they have already uploaded a resume before
    const currentUser = getCurrentUser();
    if (currentUser && currentUser.resumeScore) {
      setUserProfile(currentUser);
      setPhase("done");
    }
  }, []);

  const handleUpload = async (file: File) => {
    setResumeName(file.name);
    setPhase("parsing");
    setStep(0);
    setErrorMsg(null);

    // Visual steps interval
    const interval = setInterval(() => {
      setStep((prev) => Math.min(steps.length - 1, prev + 1));
    }, 4500 / steps.length);

    try {
      const res = await api.uploadResume(file, false);
      clearInterval(interval);
      setStep(steps.length);

      const localUser = getCurrentUser() || {};
      const updatedProfile = {
        ...localUser,
        name: res.profile?.name || localUser.name || "User",
        title: res.profile?.summary || localUser.title || "Software Specialist",
        email: res.profile?.email || localUser.email || "",
        location: res.profile?.location || localUser.location || "Remote",
        resumeScore: res.profile?.resume_score ?? 80,
        atsScore: res.profile?.ats_score ?? 85,
        skills: res.profile?.skills || [],
        missingSkills: res.profile?.missing_skills || [],
        improvements: res.profile?.improvements || [],
      };
      
      localStorage.setItem("aria.user", JSON.stringify(updatedProfile));
      setUserProfile(updatedProfile);

      setTimeout(() => {
        setPhase("done");
      }, 500);
    } catch (err: any) {
      clearInterval(interval);
      setPhase("idle");
      setErrorMsg(err.message || "Failed to upload and analyze resume.");
      console.error(err);
    }
  };

  const handleExportPDF = () => {
    if (userProfile) {
      exportResumeReport(userProfile);
    }
  };

  return (
    <>
      <PageHeader
        title="Resume Analyzer"
        subtitle="Upload your resume. Aria does the rest."
        actions={
          phase === "done" && userProfile ? (
            <button
              onClick={handleExportPDF}
              className="inline-flex items-center gap-1.5 rounded-full bg-foreground text-background px-4 py-2 text-sm font-medium hover:opacity-90 cursor-pointer"
            >
              <Download className="h-3.5 w-3.5" /> Export PDF report
            </button>
          ) : undefined
        }
      />

      {errorMsg && (
        <div className="mb-4 p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm">
          {errorMsg}
        </div>
      )}

      <AnimatePresence mode="wait">
        {phase === "idle" && (
          <motion.div key="idle" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.4 }}>
            <label className="block cursor-pointer rounded-3xl border-2 border-dashed border-border bg-card hover:border-accent hover:bg-muted/40 transition-colors p-16 text-center">
              <input
                type="file"
                accept=".pdf,.docx,.txt"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleUpload(file);
                }}
              />
              <div className="mx-auto h-14 w-14 rounded-2xl bg-muted flex items-center justify-center">
                <Upload className="h-6 w-6 text-accent" />
              </div>
              <div className="mt-5 font-display text-xl">Drop your resume here</div>
              <p className="mt-1 text-sm text-muted-foreground">PDF, DOCX or TXT · up to 5MB</p>
              <span className="mt-6 inline-block rounded-full bg-foreground text-background px-5 py-2 text-sm font-medium hover:opacity-90">
                Browse files
              </span>
            </label>
          </motion.div>
        )}

        {phase === "parsing" && (
          <motion.div key="parsing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="rounded-3xl border border-border bg-card p-10">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 rounded-xl bg-muted flex items-center justify-center">
                <FileText className="h-5 w-5 text-accent" />
              </div>
              <div>
                <div className="font-display text-lg truncate max-w-md">{resumeName}</div>
                <div className="text-xs text-muted-foreground">Aria is reading carefully...</div>
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

        {phase === "done" && userProfile && (
          <motion.div key="done" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.5 }} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
                <div className="text-xs uppercase tracking-[0.14em] text-muted-foreground mb-4">Resume strength</div>
                <Ring value={userProfile.resumeScore} label="Strong" sub="Top 15% in your field" />
              </div>
              <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
                <div className="text-xs uppercase tracking-[0.14em] text-muted-foreground mb-4">ATS compatibility</div>
                <Ring value={userProfile.atsScore} label="Excellent" sub="Will parse cleanly everywhere" />
              </div>
            </div>

            <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
              <div className="font-display text-lg mb-1">Skills detected</div>
              <p className="text-xs text-muted-foreground mb-4">Aria found {userProfile.skills?.length || 0} skills in your resume.</p>
              <div className="flex flex-wrap gap-1.5">
                {userProfile.skills?.map((s: string) => (
                  <span key={s} className="text-xs px-2.5 py-1 rounded-full bg-muted">{s}</span>
                )) || <div className="text-xs text-muted-foreground">No skills detected.</div>}
              </div>
            </div>

            {userProfile.missingSkills && userProfile.missingSkills.length > 0 && (
              <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
                <div className="font-display text-lg mb-1">Skills that would unlock more roles</div>
                <p className="text-xs text-muted-foreground mb-4">Adding any of these would surface additional matches.</p>
                <div className="flex flex-wrap gap-1.5">
                  {userProfile.missingSkills.map((s: string) => (
                    <span key={s} className="text-xs px-2.5 py-1 rounded-full border border-dashed border-accent text-accent">+ {s}</span>
                  ))}
                </div>
              </div>
            )}

            <div className="rounded-2xl bg-foreground text-background p-6">
              <div className="font-display text-lg">Actionable wins to push your score higher</div>
              <ul className="mt-3 space-y-2 text-sm text-background/80">
                {userProfile.improvements && userProfile.improvements.length > 0 ? (
                  userProfile.improvements.map((imp: string, i: number) => (
                    <li key={i}>· {imp}</li>
                  ))
                ) : (
                  <>
                    <li>· Quantify impact in your last two roles (revenue, latency, NPS).</li>
                    <li>· Move the skills section above experience for ATS visibility.</li>
                    <li>· Replace "responsible for" phrasing with action verbs.</li>
                  </>
                )}
              </ul>
              <button onClick={() => setPhase("idle")} className="mt-5 rounded-full bg-background/10 hover:bg-background/20 text-sm px-4 py-2 cursor-pointer">
                Upload another
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
