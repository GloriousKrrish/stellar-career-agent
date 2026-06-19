"use client";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, Upload, FileText, CheckCircle2, ArrowRight, ArrowLeft, Loader2, Rocket } from "lucide-react";
import { completeOnboarding } from "@/lib/auth";

export const Route = createFileRoute("/app/onboarding")({
  head: () => ({
    meta: [
      { title: "Welcome to Aria — Let's set you up" },
      { name: "description", content: "Upload your resume, confirm preferences, and launch your first AI job search." },
    ],
  }),
  component: OnboardingWizard,
});

type StepId = "welcome" | "resume" | "preferences" | "launch";
const STEPS: { id: StepId; label: string }[] = [
  { id: "welcome", label: "Welcome" },
  { id: "resume", label: "Resume" },
  { id: "preferences", label: "Preferences" },
  { id: "launch", label: "Launch" },
];

const ROLES = ["Product Engineer", "Product Designer", "Staff Engineer", "AI PM", "Founding Engineer", "Design Engineer"];
const LOCATIONS = ["Remote", "San Francisco", "New York", "London", "Berlin", "Anywhere"];
const SENIORITY = ["Mid", "Senior", "Staff", "Principal"];

const PARSE_STEPS = ["Reading file", "Parsing structure", "Extracting skills", "Scoring ATS", "Compiling profile"];

function OnboardingWizard() {
  const navigate = useNavigate();
  const [stepIdx, setStepIdx] = useState(0);
  const step = STEPS[stepIdx];

  // Resume state
  const [resumeName, setResumeName] = useState<string | null>(null);
  const [parsing, setParsing] = useState(false);
  const [parseStep, setParseStep] = useState(0);
  const [parsed, setParsed] = useState(false);

  // Preferences state
  const [roles, setRoles] = useState<string[]>(["Product Engineer"]);
  const [locations, setLocations] = useState<string[]>(["Remote"]);
  const [seniority, setSeniority] = useState("Senior");
  const [salary, setSalary] = useState(180);

  // Launch state
  const [launching, setLaunching] = useState(false);

  const handleFile = (name = "alex_morgan_resume.pdf") => {
    setResumeName(name);
    setParsing(true);
    setParseStep(0);
    setParsed(false);
    PARSE_STEPS.forEach((_, i) => setTimeout(() => setParseStep(i + 1), 500 * (i + 1)));
    setTimeout(() => { setParsing(false); setParsed(true); }, 500 * PARSE_STEPS.length + 300);
  };

  const toggle = (arr: string[], v: string, setter: (a: string[]) => void) =>
    setter(arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);

  const next = () => setStepIdx((i) => Math.min(STEPS.length - 1, i + 1));
  const back = () => setStepIdx((i) => Math.max(0, i - 1));

  const launch = () => {
    setLaunching(true);
    setTimeout(() => {
      completeOnboarding();
      navigate({ to: "/app/jobs" });
    }, 1800);
  };

  const canAdvance = (() => {
    if (step.id === "resume") return parsed;
    if (step.id === "preferences") return roles.length > 0 && locations.length > 0;
    return true;
  })();

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="max-w-2xl mx-auto px-6 py-12">
        {/* Progress */}
        <div className="flex items-center gap-2 mb-10">
          {STEPS.map((s, i) => (
            <div key={s.id} className="flex-1 flex items-center gap-2">
              <div className="flex-1">
                <div className={`h-1 rounded-full transition-colors ${i <= stepIdx ? "bg-accent" : "bg-muted"}`} />
                <div className={`mt-2 text-[11px] uppercase tracking-[0.14em] ${i === stepIdx ? "text-foreground" : "text-muted-foreground"}`}>
                  {s.label}
                </div>
              </div>
            </div>
          ))}
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={step.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
          >
            {step.id === "welcome" && (
              <div className="text-center py-6">
                <div className="mx-auto h-14 w-14 rounded-2xl bg-foreground text-background flex items-center justify-center">
                  <Sparkles className="h-6 w-6" />
                </div>
                <h1 className="mt-6 font-display text-4xl tracking-tight text-balance">Welcome. I'm Aria.</h1>
                <p className="mt-3 text-muted-foreground max-w-md mx-auto">
                  Six agents are about to start working on your job search. Three quick steps and we'll launch your first run.
                </p>
                <div className="mt-8 grid grid-cols-3 gap-3 text-left">
                  {[
                    { n: "1", t: "Upload your resume", d: "Aria reads it in seconds." },
                    { n: "2", t: "Confirm preferences", d: "Roles, location, comp." },
                    { n: "3", t: "Launch your search", d: "Agents go to work." },
                  ].map((c) => (
                    <div key={c.n} className="rounded-2xl border border-border bg-card p-4">
                      <div className="text-xs text-accent font-display">{c.n}</div>
                      <div className="mt-2 text-sm font-medium">{c.t}</div>
                      <div className="text-xs text-muted-foreground mt-0.5">{c.d}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {step.id === "resume" && (
              <div>
                <h2 className="font-display text-2xl">Upload your resume</h2>
                <p className="text-sm text-muted-foreground mt-1">PDF, DOCX or TXT · up to 5MB. Aria parses it locally.</p>

                {!resumeName && (
                  <div
                    onClick={() => handleFile()}
                    className="mt-6 cursor-pointer rounded-3xl border-2 border-dashed border-border bg-card hover:border-accent hover:bg-muted/40 transition-colors p-12 text-center"
                  >
                    <div className="mx-auto h-12 w-12 rounded-2xl bg-muted flex items-center justify-center">
                      <Upload className="h-5 w-5 text-accent" />
                    </div>
                    <div className="mt-4 font-display text-lg">Drop your resume here</div>
                    <p className="mt-1 text-xs text-muted-foreground">or click to browse</p>
                  </div>
                )}

                {resumeName && (
                  <div className="mt-6 rounded-2xl border border-border bg-card p-6">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-xl bg-muted flex items-center justify-center">
                        <FileText className="h-4 w-4 text-accent" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm truncate">{resumeName}</div>
                        <div className="text-xs text-muted-foreground">
                          {parsing ? "Aria is reading..." : parsed ? "Ready" : ""}
                        </div>
                      </div>
                      {parsed && (
                        <button onClick={() => { setResumeName(null); setParsed(false); }} className="text-xs text-muted-foreground hover:text-foreground">
                          Replace
                        </button>
                      )}
                    </div>
                    <div className="mt-5 space-y-2">
                      {PARSE_STEPS.map((s, i) => (
                        <div key={s} className="flex items-center gap-2 text-xs">
                          <div className={`h-4 w-4 rounded-full flex items-center justify-center ${i < parseStep ? "bg-accent text-accent-foreground" : "bg-muted text-muted-foreground"}`}>
                            {i < parseStep ? <CheckCircle2 className="h-2.5 w-2.5" /> : <span className="h-1 w-1 rounded-full bg-current" />}
                          </div>
                          <span className={i < parseStep ? "text-foreground" : "text-muted-foreground"}>{s}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {step.id === "preferences" && (
              <div>
                <h2 className="font-display text-2xl">Confirm your preferences</h2>
                <p className="text-sm text-muted-foreground mt-1">We'll only show roles that match these. Edit anytime later.</p>

                <div className="mt-6 space-y-6">
                  <Group label="Roles you want">
                    <div className="flex flex-wrap gap-2">
                      {ROLES.map((r) => (
                        <Chip key={r} active={roles.includes(r)} onClick={() => toggle(roles, r, setRoles)}>{r}</Chip>
                      ))}
                    </div>
                  </Group>

                  <Group label="Locations">
                    <div className="flex flex-wrap gap-2">
                      {LOCATIONS.map((l) => (
                        <Chip key={l} active={locations.includes(l)} onClick={() => toggle(locations, l, setLocations)}>{l}</Chip>
                      ))}
                    </div>
                  </Group>

                  <Group label="Seniority">
                    <div className="flex flex-wrap gap-2">
                      {SENIORITY.map((l) => (
                        <Chip key={l} active={seniority === l} onClick={() => setSeniority(l)}>{l}</Chip>
                      ))}
                    </div>
                  </Group>

                  <Group label={`Minimum base salary · $${salary}k`}>
                    <input
                      type="range" min={80} max={400} step={10} value={salary}
                      onChange={(e) => setSalary(Number(e.target.value))}
                      className="w-full accent-foreground"
                    />
                    <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
                      <span>$80k</span><span>$400k</span>
                    </div>
                  </Group>
                </div>
              </div>
            )}

            {step.id === "launch" && (
              <div className="text-center py-4">
                <div className="mx-auto h-14 w-14 rounded-2xl bg-foreground text-background flex items-center justify-center">
                  {launching ? <Loader2 className="h-6 w-6 animate-spin" /> : <Rocket className="h-6 w-6" />}
                </div>
                <h2 className="mt-6 font-display text-3xl tracking-tight">
                  {launching ? "Spinning up your agents..." : "Ready to launch"}
                </h2>
                <p className="mt-2 text-muted-foreground max-w-md mx-auto text-sm">
                  {launching
                    ? "Discovery is crawling 40+ sources. Matching is scoring fit. You'll see results stream in."
                    : "Hit launch and the Discovery, Matching and Auto Apply agents will start working on your search."}
                </p>

                <div className="mt-8 rounded-2xl border border-border bg-card p-5 text-left">
                  <div className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground mb-3">First run summary</div>
                  <Row label="Resume" value={resumeName || "—"} />
                  <Row label="Roles" value={roles.join(" · ")} />
                  <Row label="Locations" value={locations.join(" · ")} />
                  <Row label="Seniority" value={seniority} />
                  <Row label="Min comp" value={`$${salary}k`} />
                </div>
              </div>
            )}
          </motion.div>
        </AnimatePresence>

        {/* Nav */}
        <div className="mt-10 flex items-center justify-between">
          <button
            onClick={back}
            disabled={stepIdx === 0 || launching}
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground disabled:opacity-30"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back
          </button>
          <button
            onClick={() => { completeOnboarding(); navigate({ to: "/app/dashboard" }); }}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            Skip for now
          </button>
          {step.id !== "launch" ? (
            <button
              onClick={next}
              disabled={!canAdvance}
              className="inline-flex items-center gap-1.5 rounded-full bg-foreground text-background px-5 py-2 text-sm font-medium disabled:opacity-40 hover:opacity-90"
            >
              Continue <ArrowRight className="h-3.5 w-3.5" />
            </button>
          ) : (
            <button
              onClick={launch}
              disabled={launching}
              className="inline-flex items-center gap-1.5 rounded-full bg-foreground text-background px-5 py-2 text-sm font-medium disabled:opacity-60 hover:opacity-90"
            >
              {launching ? "Launching..." : "Launch first search"} <Rocket className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function Group({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs font-medium text-muted-foreground mb-2">{label}</div>
      {children}
    </div>
  );
}

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`text-xs px-3 py-1.5 rounded-full border transition ${
        active ? "border-foreground bg-foreground text-background" : "border-border bg-card text-foreground hover:bg-muted"
      }`}
    >
      {children}
    </button>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 py-1.5 text-sm border-b border-border last:border-0">
      <span className="text-muted-foreground text-xs uppercase tracking-wider">{label}</span>
      <span className="text-foreground text-right truncate">{value}</span>
    </div>
  );
}
