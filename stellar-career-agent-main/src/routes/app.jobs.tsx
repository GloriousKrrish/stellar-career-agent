"use client";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Filter, MapPin, Sparkles, Loader2, Globe, Search, DollarSign, Calendar, ExternalLink, AlertCircle, FileText, CheckCircle2 } from "lucide-react";
import { useEffect, useState, useMemo } from "react";
import { PageHeader } from "@/components/shell/sidebar";
import { Stagger, StaggerItem, HoverLift } from "@/components/motion/primitives";
import { getWorkflowJobs, listWorkflows, directSearchJobs, getMe } from "@/lib/api";

export const Route = createFileRoute("/app/jobs")({
  head: () => ({
    meta: [
      { title: "Job Search — Aria" },
      { name: "description", content: "Search and filter real jobs from across the web." },
    ],
  }),
  component: JobsPage,
});

function DirectJobCard({ job }: { job: any }) {
  const badgeColor = job.source === "NAUKRI" 
    ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20" 
    : "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20";
    
  return (
    <HoverLift>
      <div className="rounded-2xl border border-border bg-card p-5 shadow-soft hover:shadow-elegant transition-all">
        <div className="flex items-start gap-4">
          <div className="h-12 w-12 rounded-xl bg-foreground text-background flex items-center justify-center font-display text-lg flex-shrink-0">
            {job.company?.[0]?.toUpperCase() || "?"}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">{job.company}</span>
                  <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold border ${badgeColor}`}>
                    {job.source}
                  </span>
                </div>
                <div className="font-display text-lg leading-tight mt-0.5">{job.title}</div>
              </div>
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1"><MapPin className="h-3.5 w-3.5 text-accent" />{job.location || "Remote"}</span>
              <span className="inline-flex items-center gap-1"><DollarSign className="h-3.5 w-3.5 text-accent" />{job.salary || "Undisclosed"}</span>
              <span className="inline-flex items-center gap-1"><Calendar className="h-3.5 w-3.5 text-accent" />{job.posted_at || "Recently"}</span>
            </div>

            <div className="mt-4 flex items-center justify-between pt-3 border-t border-border/50">
              <span className="text-[11px] text-muted-foreground">Real-time source listing</span>
              <a
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs bg-foreground text-background px-3.5 py-2 rounded-full font-medium hover:opacity-90 transition shadow-sm"
              >
                Apply Direct <ExternalLink className="h-3 w-3" />
              </a>
            </div>
          </div>
        </div>
      </div>
    </HoverLift>
  );
}

function JobCard({ job, runId }: { job: any; runId: string }) {
  const matchScore = job.overall_match || 0;
  
  // Format source portal display
  const getSourceDisplay = (src: string) => {
    const s = src.toLowerCase();
    if (s.includes("weworkremotely")) return "WeWorkRemotely";
    if (s.includes("glassdoor")) return "Glassdoor";
    if (s.includes("naukri")) return "Naukri";
    return src || "Web";
  };

  return (
    <HoverLift>
      <Link
        to="/app/jobs/$jobId"
        params={{ jobId: job.id }}
        search={{ runId }}
        className="block rounded-2xl border border-border bg-card p-5 shadow-soft hover:shadow-elegant transition-all"
      >
        <div className="flex items-start gap-4">
          <div className="h-12 w-12 rounded-xl bg-foreground text-background flex items-center justify-center font-display text-lg flex-shrink-0">
            {job.company?.[0]?.toUpperCase() || "?"}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">{job.company}</span>
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-accent/10 text-accent border border-accent/20">
                    <Globe className="h-2.5 w-2.5" /> {getSourceDisplay(job.source)}
                  </span>
                </div>
                <div className="font-display text-lg leading-tight mt-0.5">{job.title}</div>
              </div>
              <div className="flex items-center gap-1.5 flex-shrink-0">
                <div className="relative h-12 w-12">
                  <svg viewBox="0 0 48 48" className="h-full w-full -rotate-90">
                    <circle cx="24" cy="24" r="20" stroke="oklch(0.91 0.012 75)" strokeWidth="3" fill="none" />
                    <circle cx="24" cy="24" r="20" stroke="oklch(0.62 0.07 55)" strokeWidth="3" strokeLinecap="round" fill="none"
                      strokeDasharray={2 * Math.PI * 20} strokeDashoffset={2 * Math.PI * 20 * (1 - matchScore / 100)} />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center text-xs font-medium">{matchScore}%</div>
                </div>
              </div>
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1"><MapPin className="h-3 w-3" />{job.location || "Remote"}</span>
              <span>{job.remote || "Remote"}</span>
              <span>{job.salary || "N/A"}</span>
              <span>{job.experience || "Mid"}</span>
            </div>

            {job.skills && job.skills.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {job.skills.slice(0, 5).map((s: string) => (
                  <span key={s} className="text-[11px] px-2 py-0.5 rounded-md bg-muted text-muted-foreground">{s}</span>
                ))}
              </div>
            )}

            {job.ai_recommendation && (
              <div className="mt-4 flex items-start gap-2 text-xs text-foreground/80 bg-muted/50 rounded-lg p-3">
                <Sparkles className="h-3.5 w-3.5 text-accent flex-shrink-0 mt-0.5" />
                <span>{job.ai_recommendation}</span>
              </div>
            )}

            <div className="mt-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs rounded-full bg-foreground text-background px-3 py-1.5 hover:opacity-90">View Match Details</span>
              </div>
            </div>
          </div>
        </div>
      </Link>
    </HoverLift>
  );
}

const REMOTE_OPTIONS = ["Remote", "Hybrid", "Onsite"] as const;
const EXP_OPTIONS = ["Entry", "Mid", "Senior", "Staff", "Principal"] as const;

function JobsPage() {
  const [activeTab, setActiveTab] = useState<"direct" | "ai">("direct");
  const [user, setUser] = useState<any>(null);

  // Direct search state
  const [role, setRole] = useState("");
  const [location, setLocation] = useState("");
  const [salaryTarget, setSalaryTarget] = useState("");
  const [directJobs, setDirectJobs] = useState<any[]>([]);
  const [directLoading, setDirectLoading] = useState(false);
  const [directError, setDirectError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  // AI matches state
  const [q, setQ] = useState("");
  const [remote, setRemote] = useState<string[]>([]);
  const [exp, setExp] = useState<string[]>([]);
  
  const [runId, setRunId] = useState<string | null>(null);
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadUserAndAIJobs() {
      try {
        const currentUser = await getMe();
        setUser(currentUser);
      } catch (_) {}

      try {
        let activeRunId = window.localStorage.getItem("aria.run_id");
        if (!activeRunId) {
          const list = await listWorkflows();
          if (list.workflows && list.workflows.length > 0) {
            activeRunId = list.workflows[0].run_id;
            if (activeRunId) {
              window.localStorage.setItem("aria.run_id", activeRunId);
            }
          }
        }

        if (activeRunId) {
          setRunId(activeRunId);
          const data = await getWorkflowJobs(activeRunId);
          setJobs(data.jobs || []);
        } else {
          setJobs([]);
        }
      } catch (err: any) {
        setError(err.message || "Failed to load AI matches");
      } finally {
        setLoading(false);
      }
    }
    loadUserAndAIJobs();
  }, []);

  const handleDirectSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!role.trim()) {
      setDirectError("Job Role is required.");
      return;
    }
    setDirectLoading(true);
    setDirectError(null);
    setDirectJobs([]);
    try {
      const data = await directSearchJobs(role, location, salaryTarget);
      setDirectJobs(data.jobs || []);
      setHasSearched(true);
    } catch (err: any) {
      setDirectError("Search temporarily unavailable.");
    } finally {
      setDirectLoading(false);
    }
  };

  const filteredAIJobs = useMemo(() => {
    return jobs.filter((j) => {
      if (q && !`${j.title} ${j.company} ${(j.skills || []).join(" ")}`.toLowerCase().includes(q.toLowerCase())) return false;
      if (remote.length && !remote.includes(j.remote)) return false;
      if (exp.length && !exp.includes(j.experience)) return false;
      return true;
    });
  }, [jobs, q, remote, exp]);

  const toggleFilter = (arr: string[], v: string, set: (a: string[]) => void) =>
    set(arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);

  const resumeExists = user && (user.skills?.length > 0 || user.raw_text?.length > 0);

  return (
    <>
      <PageHeader 
        title="Job Search Hub" 
        subtitle="Search manually or explore agentic matches." 
      />

      {/* Tab Switcher */}
      <div className="flex gap-2 p-1 bg-muted rounded-xl w-fit mb-8">
        <button
          onClick={() => setActiveTab("direct")}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all ${
            activeTab === "direct" 
              ? "bg-background text-foreground shadow-sm" 
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Search className="h-4 w-4" />
          Direct Job Search
        </button>
        <button
          onClick={() => setActiveTab("ai")}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all ${
            activeTab === "ai" 
              ? "bg-background text-foreground shadow-sm" 
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Sparkles className="h-4 w-4 text-accent" />
          AI Agent Matches
        </button>
      </div>

      {activeTab === "direct" ? (
        <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-8">
          {/* Direct Search Panel */}
          <aside className="h-fit">
            <form onSubmit={handleDirectSearch} className="rounded-2xl border border-border bg-gradient-to-br from-card to-background/50 p-6 shadow-soft space-y-5">
              <div className="flex items-center gap-2 text-xs uppercase tracking-[0.14em] text-muted-foreground border-b border-border pb-3">
                <Filter className="h-3.5 w-3.5" /> Search Filters
              </div>

              {/* Resume integration status */}
              <div className="p-3 bg-muted/60 rounded-xl border border-border/80 text-xs">
                {resumeExists ? (
                  <div className="flex items-start gap-2 text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold">Resume parsing active</span>
                      <p className="text-[10px] text-muted-foreground mt-0.5">Manual search results will be sorted by profile compatibility.</p>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-start gap-2 text-muted-foreground">
                    <FileText className="h-4 w-4 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold">No resume loaded (Optional)</span>
                      <p className="text-[10px] mt-0.5">Upload a resume in the <Link to="/app/resume" className="text-accent underline font-medium">Analyzer</Link> to automatically rank search results.</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Job Role (Required) */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Job Role *</label>
                <div className="relative">
                  <Search className="absolute left-3.5 top-3 h-4 w-4 text-muted-foreground" />
                  <input
                    type="text"
                    required
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    placeholder="e.g. Full Stack Developer"
                    className="w-full rounded-xl border border-border bg-background pl-10 pr-3 py-2.5 text-sm outline-none focus:border-accent text-foreground transition"
                  />
                </div>
              </div>

              {/* Location (Optional) */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Location (Optional)</label>
                <div className="relative">
                  <MapPin className="absolute left-3.5 top-3 h-4 w-4 text-muted-foreground" />
                  <input
                    type="text"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder="e.g. Pune, Bangalore, Remote"
                    className="w-full rounded-xl border border-border bg-background pl-10 pr-3 py-2.5 text-sm outline-none focus:border-accent text-foreground transition"
                  />
                </div>
              </div>

              {/* Salary Target (Optional) */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Salary Target (Optional)</label>
                <select
                  value={salaryTarget}
                  onChange={(e) => setSalaryTarget(e.target.value)}
                  className="w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm outline-none focus:border-accent text-foreground transition appearance-none cursor-pointer"
                >
                  <option value="">Any Salary Target (Flexible)</option>
                  <option value="₹5 LPA">₹5 LPA</option>
                  <option value="₹8 LPA">₹8 LPA</option>
                  <option value="₹12 LPA">₹12 LPA</option>
                  <option value="₹20 LPA">₹20 LPA</option>
                  <option value="₹30 LPA+">₹30 LPA+</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={directLoading}
                className="w-full rounded-full bg-foreground text-background py-3 text-sm font-semibold hover:opacity-90 transition shadow-elegant flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {directLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Searching Real Web...
                  </>
                ) : (
                  <>
                    <Search className="h-4 w-4" />
                    Search Jobs
                  </>
                )}
              </button>
            </form>
          </aside>

          {/* Results Area */}
          <div className="space-y-4">
            {directError && (
              <div className="flex items-start gap-3 rounded-2xl border border-red-200 dark:border-red-900/30 bg-red-50 dark:bg-red-950/20 p-4 text-sm text-red-500">
                <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold">Search temporarily unavailable.</span>
                  <p className="text-xs text-muted-foreground mt-1">Both Glassdoor and Naukri web queries failed to fetch listing data. Please check your connectivity or try again in a moment.</p>
                </div>
              </div>
            )}

            {directLoading ? (
              <div className="flex flex-col items-center justify-center py-20 gap-4">
                <Loader2 className="h-10 w-10 animate-spin text-accent" />
                <div className="text-center">
                  <div className="font-display text-lg">Querying Target Portals...</div>
                  <p className="text-xs text-muted-foreground max-w-xs mt-1">Crawling live listings from Glassdoor and Naukri. This does not use slow agent reasoning steps.</p>
                </div>
              </div>
            ) : (
              <Stagger className="space-y-4">
                {directJobs.map((j) => (
                  <StaggerItem key={j.id}>
                    <DirectJobCard job={j} />
                  </StaggerItem>
                ))}

                {directJobs.length === 0 && !directError && (
                  <div className="rounded-3xl border border-dashed border-border bg-card p-16 text-center text-muted-foreground">
                    <div className="font-display text-lg text-foreground">
                      {hasSearched ? "No matching roles found" : "Direct Job Discovery Portal"}
                    </div>
                    <p className="text-sm mt-1.5 max-w-sm mx-auto">
                      {hasSearched
                        ? "We couldn't find listings matching your specific role on Glassdoor or Naukri. Try a slightly wider keyword."
                        : "Enter a job role and location to query real-time jobs from Naukri and Glassdoor. Operating completely independent of agent steps."}
                    </p>
                  </div>
                )}
              </Stagger>
            )}
          </div>
        </div>
      ) : (
        /* AI Agent matches tab */
        <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-6">
          <aside className="space-y-5">
            <div className="rounded-2xl border border-border bg-card p-4 shadow-soft">
              <div className="flex items-center gap-2 text-xs uppercase tracking-[0.14em] text-muted-foreground mb-3">
                <Filter className="h-3.5 w-3.5" /> Filters
              </div>
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Role, company, skill"
                className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent text-foreground"
              />

              <div className="mt-5">
                <div className="text-xs font-medium mb-2">Work mode</div>
                <div className="flex flex-wrap gap-1.5">
                  {REMOTE_OPTIONS.map((o) => (
                    <button key={o} onClick={() => toggleFilter(remote, o, setRemote)}
                      className={`text-xs px-2.5 py-1 rounded-full border transition ${remote.includes(o) ? "bg-foreground text-background border-foreground" : "border-border hover:bg-muted"}`}>
                      {o}
                    </button>
                  ))}
                </div>
              </div>

              <div className="mt-5">
                <div className="text-xs font-medium mb-2">Experience</div>
                <div className="flex flex-wrap gap-1.5">
                  {EXP_OPTIONS.map((o) => (
                    <button key={o} onClick={() => toggleFilter(exp, o, setExp)}
                      className={`text-xs px-2.5 py-1 rounded-full border transition ${exp.includes(o) ? "bg-foreground text-background border-foreground" : "border-border hover:bg-muted"}`}>
                      {o}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </aside>

          <div>
            {error && (
              <div className="mb-4 text-xs text-red-500 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/30 rounded-xl p-3">
                {error}
              </div>
            )}

            {loading ? (
              <div className="flex h-[40vh] items-center justify-center">
                <div className="flex flex-col items-center gap-3">
                  <Loader2 className="h-8 w-8 animate-spin text-accent" />
                  <span className="text-sm text-muted-foreground">Fetching scored fits...</span>
                </div>
              </div>
            ) : (
              <Stagger className="space-y-3">
                {filteredAIJobs.map((j) => (
                  <StaggerItem key={j.id}><JobCard job={j} runId={runId || ""} /></StaggerItem>
                ))}
                {filteredAIJobs.length === 0 && (
                  <div className="rounded-3xl border border-dashed border-border bg-card p-12 text-center text-muted-foreground">
                    <div className="font-display text-lg text-foreground">No jobs found</div>
                    <p className="text-sm mt-1">
                      {runId ? "Try widening your search filters or launching a new workflow run." : "Upload a resume on the dashboard to kick off your first search run."}
                    </p>
                  </div>
                )}
              </Stagger>
            )}
          </div>
        </div>
      )}
    </>
  );
}
