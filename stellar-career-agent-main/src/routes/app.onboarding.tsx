"use client";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, Upload, FileText, CheckCircle2, ArrowRight, ArrowLeft, Loader2, Rocket, AlertCircle } from "lucide-react";
import { completeOnboarding } from "@/lib/auth";
import { uploadResume, startWorkflow } from "@/lib/api";

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

const PARSE_STEPS = ["Reading file", "Parsing structure", "Extracting skills", "Scoring ATS", "Compiling profile"];

const SALARY_STEPS = [3, 5, 8, 12, 18, 25, 40];

function OnboardingWizard() {
  const navigate = useNavigate();
  const [stepIdx, setStepIdx] = useState(0);
  const step = STEPS[stepIdx];

  // Resume state
  const [resumeName, setResumeName] = useState<string | null>(null);
  const [parsing, setParsing] = useState(false);
  const [parseStep, setParseStep] = useState(0);
  const [parsed, setParsed] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [parsedData, setParsedData] = useState<{
    profile: any;
    career_profile: any;
  } | null>(null);

  // Dynamic preference options
  const [rolesList, setRolesList] = useState<string[]>([]);
  const [locationsList, setLocationsList] = useState<string[]>([]);
  const [seniorityList, setSeniorityList] = useState<string[]>(["Entry", "Mid", "Senior", "Staff", "Principal"]);

  // Preferences selection state
  const [roleInput, setRoleInput] = useState("");
  const [locations, setLocations] = useState<string[]>([]);
  const [seniority, setSeniority] = useState("");
  const [salaryIndex, setSalaryIndex] = useState(2); // 8 LPA by default

  // Launch state
  const [launching, setLaunching] = useState(false);

  const handleFile = async (file: File) => {
    setResumeName(file.name);
    setParsing(true);
    setParseStep(1); // Reading file
    setParsed(false);
    setError(null);
    try {
      setParseStep(2); // Parsing structure
      const res = await uploadResume(file, false);
      setParseStep(3); // Extracting skills
      setParseStep(4); // Scoring ATS
      setParseStep(5); // Compiling profile
      setRunId(res.run_id);
      window.localStorage.setItem("aria.run_id", res.run_id);
      setParsedData(res);

      if (res.career_profile) {
        const idealTitles = res.career_profile.ideal_titles || [];
        setRolesList(idealTitles);
        setRoleInput(idealTitles[0] || "");
        setSeniority(res.career_profile.seniority_level || "Senior");
        
        // Match the closest step in SALARY_STEPS
        const profileMin = res.career_profile.salary_min || 800000; // in INR
        const minLPA = Math.round(profileMin / 100000);
        let closestIdx = 0;
        let minDiff = Math.abs(SALARY_STEPS[0] - minLPA);
        for (let i = 1; i < SALARY_STEPS.length; i++) {
          const diff = Math.abs(SALARY_STEPS[i] - minLPA);
          if (diff < minDiff) {
            minDiff = diff;
            closestIdx = i;
          }
        }
        setSalaryIndex(closestIdx);
      } else {
        setRolesList(["Software Engineer"]);
        setRoleInput("Software Engineer");
        setSeniority("Senior");
        setSalaryIndex(2); // 8 LPA
      }

      if (res.profile) {
        const location = res.profile.location;
        const locs = [location, "Remote", "Anywhere"].filter((v, i, self) => v && self.indexOf(v) === i) as string[];
        setLocationsList(locs);
        setLocations([location || "Remote"]);
      } else {
        setLocationsList(["Remote", "Anywhere"]);
        setLocations(["Remote"]);
      }

      setParsed(true);
    } catch (err: any) {
      setError(err.message || "Failed to parse resume");
      setResumeName(null);
    } finally {
      setParsing(false);
    }
  };

  const triggerFileInput = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".pdf,.docx,.txt";
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        handleFile(file);
      }
    };
    input.click();
  };

  const toggle = (arr: string[], v: string, setter: (a: string[]) => void) =>
    setter(arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);

  const next = () => setStepIdx((i) => Math.min(STEPS.length - 1, i + 1));
  const back = () => setStepIdx((i) => Math.max(0, i - 1));

  const launch = async () => {
    setLaunching(true);
    setError(null);
    try {
      await startWorkflow({
        role: roleInput,
        location: locations[0] || "Remote",
        remotePreference: locations.includes("Remote") ? "Remote" : "Onsite",
        experienceLevel: seniority,
        salaryMin: SALARY_STEPS[salaryIndex] * 100000,
        runId: runId || undefined,
      });
      completeOnboarding();
      navigate({ to: "/app/jobs" });
    } catch (err: any) {
      setError(err.message || "Failed to launch job search pipeline");
    } finally {
      setLaunching(false);
    }
  };

  const canAdvance = (() => {
    if (step.id === "resume") return parsed && roleInput.trim().length > 0;
    if (step.id === "preferences") return roleInput.trim().length > 0 && locations.length > 0;
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

        {error && (
          <div className="mb-6 p-4 rounded-xl border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/20 text-red-500 text-sm flex items-center gap-3">
            <AlertCircle className="h-5 w-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

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
                <div className="mx-auto h-14 w-14 rounded-2xl bg-foreground text-background flex items-center justify-center animate-pulse">
                  <Sparkles className="h-6 w-6" />
                </div>
                <h1 className="mt-6 font-display text-4xl tracking-tight text-balance">Welcome. I'm Aria.</h1>
                <p className="mt-3 text-muted-foreground max-w-md mx-auto">
                  Six agents are about to start working on your job search. Three quick steps and we'll launch your first run.
                </p>
                <div className="mt-8 grid grid-cols-3 gap-3 text-left">
                  {[
                    { n: "1", t: "Upload your resume", d: "Aria parses it locally." },
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
                <p className="text-sm text-muted-foreground mt-1">PDF, DOCX or TXT · up to 10MB. Aria parses it instantly.</p>

                {!resumeName && (
                  <div
                    onClick={triggerFileInput}
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
                          {parsing ? "Aria is analyzing & extracting..." : parsed ? "Ready" : ""}
                        </div>
                      </div>
                      {parsed && (
                        <button
                          onClick={() => {
                            setResumeName(null);
                            setParsed(false);
                            setRunId(null);
                            setParsedData(null);
                            setRolesList([]);
                            setRoleInput("");
                            setLocationsList([]);
                            setLocations([]);
                            setSeniority("");
                            setSalaryIndex(2);
                          }}
                          className="text-xs text-muted-foreground hover:text-foreground"
                        >
                          Replace
                        </button>
                      )}
                    </div>
                    {parsing && (
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
                    )}

                    {parsed && parsedData && (
                      <div className="mt-6 border-t border-border pt-5 space-y-4">
                        <div className="rounded-2xl border border-accent/20 bg-accent/5 p-5">
                          <label className="text-sm font-semibold text-foreground block mb-2">What role are you looking for?</label>
                          <input
                            type="text"
                            value={roleInput}
                            onChange={(e) => setRoleInput(e.target.value)}
                            placeholder="e.g. AI Engineer, Frontend Developer"
                            className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent text-foreground"
                          />
                          <div className="mt-2.5 flex flex-wrap gap-1.5 items-center">
                            <span className="text-[11px] text-muted-foreground mr-1">Examples:</span>
                            {["AI Engineer", "Frontend Developer", "Backend Developer", "Data Analyst", "Product Manager"].map((ex) => (
                              <button
                                key={ex}
                                type="button"
                                onClick={() => setRoleInput(ex)}
                                className="text-[11px] px-2.5 py-1 rounded-full border border-border bg-background hover:bg-muted text-foreground transition"
                              >
                                {ex}
                              </button>
                            ))}
                          </div>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          <div>
                            <span className="text-[10px] uppercase tracking-wider text-muted-foreground">Extracted Profile</span>
                            <div className="mt-1 font-display text-base font-semibold">{parsedData.profile?.name || "Candidate"}</div>
                            <div className="text-xs text-muted-foreground">{parsedData.profile?.email} · {parsedData.profile?.location || "Remote"}</div>
                          </div>
                          <div>
                            <span className="text-[10px] uppercase tracking-wider text-muted-foreground">ATS Score</span>
                            <div className="mt-1 flex items-baseline gap-1">
                              <span className="font-display text-2xl text-accent">{parsedData.profile?.ats_score || 0}</span>
                              <span className="text-xs text-muted-foreground">/100</span>
                            </div>
                          </div>
                        </div>

                        {parsedData.profile?.skills && parsedData.profile.skills.length > 0 && (
                          <div>
                            <span className="text-[10px] uppercase tracking-wider text-muted-foreground">Extracted Skills</span>
                            <div className="mt-1.5 flex flex-wrap gap-1">
                              {parsedData.profile.skills.slice(0, 10).map((s: string) => (
                                <span key={s} className="text-[10px] px-2 py-0.5 rounded bg-muted text-foreground border border-border">
                                  {s}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {parsedData.profile?.work_history && parsedData.profile.work_history.length > 0 && (
                          <div>
                            <span className="text-[10px] uppercase tracking-wider text-muted-foreground">Work History</span>
                            <div className="mt-1.5 space-y-2">
                              {parsedData.profile.work_history.slice(0, 2).map((w: any, idx: number) => (
                                <div key={idx} className="text-xs">
                                  <div className="font-semibold text-foreground">{w.title} <span className="font-normal text-muted-foreground">at {w.company}</span></div>
                                  {w.start_date && <div className="text-[10px] text-muted-foreground">{w.start_date} - {w.end_date || "Present"}</div>}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {parsedData.profile?.education && parsedData.profile.education.length > 0 && (
                          <div>
                            <span className="text-[10px] uppercase tracking-wider text-muted-foreground">Education</span>
                            <div className="mt-1.5 space-y-1">
                              {parsedData.profile.education.slice(0, 2).map((e: any, idx: number) => (
                                <div key={idx} className="text-xs">
                                  <span className="font-semibold">{e.degree || "Degree"}</span> in {e.field || "Field"}
                                  {e.institution && <div className="text-[10px] text-muted-foreground">{e.institution} {e.year ? `· ${e.year}` : ""}</div>}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {step.id === "preferences" && (
              <div>
                <h2 className="font-display text-2xl">Confirm your preferences</h2>
                <p className="text-sm text-muted-foreground mt-1">We'll only show roles that match these. Edit anytime later.</p>

                <div className="mt-6 space-y-6">
                  <Group label="Role you want">
                    <input
                      type="text"
                      value={roleInput}
                      onChange={(e) => setRoleInput(e.target.value)}
                      placeholder="e.g. AI Engineer, Frontend Developer"
                      className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent text-foreground"
                    />
                    <div className="mt-2 flex flex-wrap gap-1.5 items-center">
                      <span className="text-[11px] text-muted-foreground mr-1">Examples:</span>
                      {["AI Engineer", "Frontend Developer", "Backend Developer", "Data Analyst", "Product Manager"].map((ex) => (
                        <button
                          key={ex}
                          type="button"
                          onClick={() => setRoleInput(ex)}
                          className="text-[11px] px-2.5 py-1 rounded-full border border-border bg-card hover:bg-muted text-foreground transition"
                        >
                          {ex}
                        </button>
                      ))}
                    </div>
                  </Group>

                  {locationsList.length > 0 && (
                    <Group label="Locations">
                      <div className="flex flex-wrap gap-2">
                        {locationsList.map((l) => (
                          <Chip key={l} active={locations.includes(l)} onClick={() => toggle(locations, l, setLocations)}>{l}</Chip>
                        ))}
                      </div>
                    </Group>
                  )}

                  <Group label="Seniority">
                    <div className="flex flex-wrap gap-2">
                      {seniorityList.map((l) => (
                        <Chip key={l} active={seniority === l} onClick={() => setSeniority(l)}>{l}</Chip>
                      ))}
                    </div>
                  </Group>

                  <Group label={`Minimum base salary · ₹${SALARY_STEPS[salaryIndex]} LPA`}>
                    <input
                      type="range" min={0} max={SALARY_STEPS.length - 1} step={1} value={salaryIndex}
                      onChange={(e) => setSalaryIndex(Number(e.target.value))}
                      className="w-full accent-foreground"
                    />
                    <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
                      <span>₹3 LPA</span><span>₹40 LPA+</span>
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
                  {launching ? "Launching search..." : "Ready to launch"}
                </h2>
                <p className="mt-2 text-muted-foreground max-w-md mx-auto text-sm">
                  {launching
                    ? "Discovery is crawling WeWorkRemotely, Glassdoor and Naukri. Scored fits will stream in."
                    : "Hit launch and the Discovery, Matching and Auto Apply agents will start working on your search."}
                </p>

                <div className="mt-8 rounded-2xl border border-border bg-card p-5 text-left">
                  <div className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground mb-3">First run summary</div>
                  <Row label="Resume" value={resumeName || "—"} />
                  <Row label="Roles" value={roleInput || "—"} />
                  <Row label="Locations" value={locations.join(" · ")} />
                  <Row label="Seniority" value={seniority} />
                  <Row label="Min comp" value={`₹${SALARY_STEPS[salaryIndex]} LPA`} />
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
