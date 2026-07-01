"use client";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Filter, MapPin, BookmarkPlus, Sparkles, Search, RefreshCw } from "lucide-react";
import { useMemo, useState, useEffect } from "react";
import { motion } from "framer-motion";
import { PageHeader } from "@/components/shell/sidebar";
import { Stagger, StaggerItem, HoverLift } from "@/components/motion/primitives";
import { api, API_BASE_URL } from "@/lib/api";
import type { Job } from "@/lib/types";
import { ApplyDialog } from "@/components/apply/apply-dialog";

export const Route = createFileRoute("/app/jobs")({
  head: () => ({
    meta: [
      { title: "Job Search — Aria" },
      { name: "description", content: "Search and filter AI-curated jobs from across the web." },
    ],
  }),
  component: JobsPage,
});

function JobCard({ job, onAutoApply }: { job: Job; onAutoApply: (job: Job) => void }) {
  const handleAddToApplications = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await api.createApplication({
        job_id: job.id,
        title: job.title,
        company: job.company,
        company_logo: job.companyLogo,
        stage: "saved",
        location: job.location,
        salary: job.salary,
        url: job.url,
      });
      alert(`Saved ${job.title} at ${job.company} to applications tracker.`);
    } catch (err) {
      console.error("Failed to add job to applications:", err);
    }
  };

  return (
    <HoverLift>
      <Link
        to="/app/jobs/$jobId"
        params={{ jobId: job.id }}
        className="block rounded-2xl border border-border bg-card p-5 shadow-soft hover:shadow-elegant transition-shadow"
      >
        <div className="flex items-start gap-4">
          <div className="h-12 w-12 rounded-xl bg-foreground text-background flex items-center justify-center font-display text-lg flex-shrink-0 select-none">
            {job.companyLogo}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-xs text-muted-foreground">{job.company} · {job.postedAt}</div>
                <div className="font-display text-lg leading-tight mt-0.5">{job.title}</div>
              </div>
              <div className="flex items-center gap-1.5 flex-shrink-0">
                <div className="relative h-12 w-12">
                  <svg viewBox="0 0 48 48" className="h-full w-full -rotate-90">
                    <circle cx="24" cy="24" r="20" stroke="oklch(0.91 0.012 75)" strokeWidth="3" fill="none" />
                    <circle cx="24" cy="24" r="20" stroke="oklch(0.62 0.07 55)" strokeWidth="3" strokeLinecap="round" fill="none"
                      strokeDasharray={2 * Math.PI * 20} strokeDashoffset={2 * Math.PI * 20 * (1 - job.match / 100)} />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center text-xs font-medium">{job.match}</div>
                </div>
              </div>
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1"><MapPin className="h-3 w-3" />{job.location}</span>
              <span>{job.remote}</span>
              <span>{job.salary || "Undisclosed"}</span>
              <span>{job.experience}</span>
              {job.source && (
                <span className="bg-muted px-2 py-0.5 rounded text-[10px] uppercase font-semibold text-muted-foreground">
                  Source: {job.source}
                </span>
              )}
            </div>

            {job.skills && job.skills.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {job.skills.slice(0, 5).map((s) => (
                  <span key={s} className="text-[11px] px-2 py-0.5 rounded-md bg-muted text-muted-foreground">{s}</span>
                ))}
              </div>
            )}

            <div className="mt-4 flex items-start gap-2 text-xs text-foreground/80 bg-muted/50 rounded-lg p-3">
              <Sparkles className="h-3.5 w-3.5 text-accent flex-shrink-0 mt-0.5" />
              <span>{job.aiRecommendation}</span>
            </div>

            <div className="mt-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    onAutoApply(job);
                  }}
                  className="text-xs rounded-full bg-accent text-accent-foreground px-3 py-1.5 hover:opacity-90 font-medium cursor-pointer"
                >
                  Auto-Apply
                </button>
                <button
                  onClick={handleAddToApplications}
                  className="text-xs rounded-full bg-foreground text-background px-3 py-1.5 hover:opacity-90 cursor-pointer"
                >
                  Save to board
                </button>
                <Link
                  to="/app/jobs/$jobId"
                  params={{ jobId: job.id }}
                  className="text-xs rounded-full border border-border px-3 py-1.5 hover:bg-muted text-foreground"
                >
                  Details
                </Link>
                {job.url && (
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="text-xs rounded-full border border-border px-3 py-1.5 hover:bg-muted text-foreground font-medium cursor-pointer"
                  >
                    Direct Link
                  </a>
                )}
              </div>
              <button
                onClick={handleAddToApplications}
                className="h-8 w-8 inline-flex items-center justify-center rounded-full hover:bg-muted text-muted-foreground cursor-pointer"
              >
                <BookmarkPlus className="h-4 w-4" />
              </button>
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
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [remote, setRemote] = useState<string[]>([]);
  const [exp, setExp] = useState<string[]>([]);
  const [selectedJobForApply, setSelectedJobForApply] = useState<Job | null>(null);

  // Manual Crawler Search state
  const [searchRole, setSearchRole] = useState("");
  const [searchLocation, setSearchLocation] = useState("");
  const [searchSalary, setSearchSalary] = useState("");
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [wsLogs, setWsLogs] = useState<string[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);

  const loadWorkflowJobs = async (runId: string) => {
    try {
      const jobsRes = await api.getWorkflowJobs(runId);
      if (jobsRes.jobs) {
        const mappedJobs = jobsRes.jobs.map((j: any) => ({
          id: j.id,
          title: j.title,
          company: j.company,
          companyLogo: j.company_logo || j.company?.[0]?.toUpperCase() || "?",
          location: j.location || "Remote",
          remote: j.remote || "Remote",
          salary: j.salary || "Undisclosed",
          salaryMin: j.salary_min || 0,
          salaryMax: j.salary_max || 0,
          experience: j.experience || "Mid",
          industry: j.industry || "Technology",
          postedAt: j.posted_at || "Just now",
          match: j.overall_match || 0,
          aiRecommendation: j.ai_recommendation || "Matched skills & experience preferences.",
          description: j.description || "",
          responsibilities: j.responsibilities || [],
          requirements: j.requirements || [],
          niceToHave: j.nice_to_have || [],
          benefits: j.benefits || [],
          skills: j.skills || [],
          url: j.url || "",
          source: j.source || "Unknown",
        }));
        setJobs(mappedJobs);
      }
    } catch (err) {
      console.error("Failed to load workflow jobs:", err);
    }
  };

  useEffect(() => {
    async function loadInitial() {
      try {
        let runId = localStorage.getItem("aria.active_run_id");
        if (runId === "manual_enqueue") {
          localStorage.removeItem("aria.active_run_id");
          runId = null;
        }
        if (!runId) {
          const workflowsRes = await api.getWorkflows();
          if (workflowsRes.workflows && workflowsRes.workflows.length > 0) {
            const sorted = [...workflowsRes.workflows].sort(
              (a, b) => new Date(b.created_at || b.updated_at).getTime() - new Date(a.created_at || a.updated_at).getTime()
            );
            runId = sorted[0].run_id;
          }
        }

        if (runId) {
          await loadWorkflowJobs(runId);

          // Check if it is currently running
          const state = await api.getWorkflowState(runId);
          if (state && (state.status === "pending" || state.status === "running")) {
            setActiveRunId(runId);
            setSearchLoading(true);
          }
        }
      } catch (err) {
        console.error("Failed to load initial workflow jobs:", err);
      } finally {
        setLoading(false);
      }
    }
    loadInitial();
  }, []);

  // Listen to active background workflow runs
  useEffect(() => {
    if (!activeRunId) return;

    const wsBase = API_BASE_URL ? API_BASE_URL.replace(/^http/, "ws") : "ws://localhost:8000";
    const socket = new WebSocket(`${wsBase}/ws/${activeRunId}`);

    socket.onopen = () => {
      setWsLogs((prev) => [...prev, "Connected to live activity stream."]);
    };

    socket.onmessage = (event) => {
      try {
        const raw = JSON.parse(event.data);
        if (raw.message) {
          setWsLogs((prev) => [...prev, raw.message].slice(-5));
        }

        // Auto reload on updates
        if (raw.event_type === "completed") {
          loadWorkflowJobs(activeRunId);
          setActiveRunId(null);
          setSearchLoading(false);
          setWsLogs([]);
        } else if (raw.event_type === "error") {
          setActiveRunId(null);
          setSearchLoading(false);
          setWsLogs([]);
          alert(`Workflow failed: ${raw.message || "Unknown error"}`);
        } else if (raw.event_type === "job_found" || raw.event_type === "match_scored") {
          loadWorkflowJobs(activeRunId);
        }
      } catch (err) {
        console.error(err);
      }
    };

    socket.onerror = () => {
      setWsLogs((prev) => [...prev, "Stream connection lost."]);
    };

    socket.onclose = () => {
      setActiveRunId(null);
      setSearchLoading(false);
    };

    return () => {
      socket.close();
    };
  }, [activeRunId]);

  const handleFindJobs = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchRole.trim()) return;

    setSearchLoading(true);
    setJobs([]); // Clear stale jobs from previous search
    setWsLogs(["Launching job discovery agents..."]);
    try {
      // Map salary options to integer INR values
      let salaryMin = 0;
      let salaryMax = 5000000;
      if (searchSalary === "3") { salaryMin = 300000; salaryMax = 800000; }
      else if (searchSalary === "6") { salaryMin = 600000; salaryMax = 1500000; }
      else if (searchSalary === "12") { salaryMin = 1200000; salaryMax = 2500000; }
      else if (searchSalary === "18") { salaryMin = 1800000; salaryMax = 3500000; }
      else if (searchSalary === "25") { salaryMin = 2500000; salaryMax = 5000000; }
      else if (searchSalary === "40") { salaryMin = 4000000; salaryMax = 12000000; }

      const remotePref = searchLocation.toLowerCase().includes("remote") ? "Remote" : "Hybrid";

      const res = await api.startWorkflow(
        searchRole,
        remotePref,
        undefined,
        searchLocation,
        salaryMin,
        salaryMax
      );

      if (res && res.run_id) {
        localStorage.setItem("aria.active_run_id", res.run_id);
        setActiveRunId(res.run_id);
        window.dispatchEvent(new CustomEvent("aria:run_started", { detail: res.run_id }));
      }
    } catch (err: any) {
      console.error(err);
      setWsLogs((prev) => [...prev, `Error starting search: ${err.message || "Service error"}`]);
      setSearchLoading(false);
    }
  };

  const filtered = useMemo(() => {
    return jobs.filter((j) => {
      if (q && !`${j.title} ${j.company} ${j.skills.join(" ")}`.toLowerCase().includes(q.toLowerCase())) return false;
      if (remote.length && !remote.includes(j.remote)) return false;
      if (exp.length && !exp.includes(j.experience)) return false;
      return true;
    });
  }, [jobs, q, remote, exp]);

  const toggle = (arr: string[], v: string, set: (a: string[]) => void) =>
    set(arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);

  return (
    <>
      <PageHeader title="Job Search" subtitle={loading ? "Finding matches..." : `${filtered.length} curated roles discovered.`} />

      {/* Crawl overlay */}
      {searchLoading && (
        <div className="mb-6 rounded-2xl border border-accent/20 bg-accent/5 p-5 shadow-soft">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-2 w-2 rounded-full bg-accent animate-pulse" />
              <div className="text-xs font-semibold uppercase tracking-[0.14em] text-accent">Real-Time Search In Progress</div>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-accent">
              <RefreshCw className="h-3.5 w-3.5 animate-spin" /> Crawling Glassdoor & Naukri...
            </div>
          </div>
          <p className="mt-2 text-sm text-foreground/80">
            Aria is scanning public listings for "<strong>{searchRole}</strong>"{searchLocation ? ` in "${searchLocation}"` : ""} — real-time scores will populate below once crawling completes.
          </p>
          {wsLogs.length > 0 && (
            <div className="mt-3 bg-card/60 rounded-xl p-3 border border-border text-[11px] font-mono text-muted-foreground max-h-[100px] overflow-y-auto space-y-1">
              {wsLogs.map((logStr, idx) => (
                <div key={idx} className="truncate">→ {logStr}</div>
              ))}
            </div>
          )}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20 text-muted-foreground text-sm">
          Loading jobs...
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-6">
          <aside className="space-y-5">
            {/* Search Execution Form */}
            <form onSubmit={handleFindJobs} className="rounded-2xl border border-border bg-card p-4 shadow-soft space-y-4">
              <div className="flex items-center gap-2 text-xs uppercase tracking-[0.14em] text-accent font-semibold">
                <Search className="h-3.5 w-3.5" /> Find Jobs
              </div>
              
              <div className="space-y-1.5">
                <label className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Job Role</label>
                <input
                  value={searchRole}
                  onChange={(e) => setSearchRole(e.target.value)}
                  placeholder="e.g. Python Developer"
                  required
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent text-foreground"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Location (Optional)</label>
                <input
                  value={searchLocation}
                  onChange={(e) => setSearchLocation(e.target.value)}
                  placeholder="e.g. Bangalore, Remote"
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent text-foreground"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Salary Target</label>
                <select
                  value={searchSalary}
                  onChange={(e) => setSearchSalary(e.target.value)}
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent text-foreground"
                >
                  <option value="">Any Salary</option>
                  <option value="3">₹3 LPA+</option>
                  <option value="6">₹6 LPA+</option>
                  <option value="12">₹12 LPA+</option>
                  <option value="18">₹18 LPA+</option>
                  <option value="25">₹25 LPA+</option>
                  <option value="40">₹40+ LPA</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={searchLoading}
                className="w-full rounded-full bg-accent text-accent-foreground py-2 text-sm font-medium hover:opacity-90 disabled:opacity-50 transition cursor-pointer"
              >
                {searchLoading ? "Searching..." : "Find Jobs"}
              </button>
            </form>

            {/* Filter Results Form */}
            <div className="rounded-2xl border border-border bg-card p-4 shadow-soft">
              <div className="flex items-center gap-2 text-xs uppercase tracking-[0.14em] text-muted-foreground mb-3">
                <Filter className="h-3.5 w-3.5" /> Filter Results
              </div>
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Filter by keyword..."
                className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent"
              />

              <div className="mt-5">
                <div className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-2">Work mode</div>
                <div className="flex flex-wrap gap-1.5">
                  {REMOTE_OPTIONS.map((o) => (
                    <button key={o} onClick={() => toggle(remote, o, setRemote)}
                      className={`text-xs px-2.5 py-1 rounded-full border transition cursor-pointer ${remote.includes(o) ? "bg-foreground text-background border-foreground" : "border-border hover:bg-muted text-foreground"}`}>
                      {o}
                    </button>
                  ))}
                </div>
              </div>

              <div className="mt-5">
                <div className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-2">Experience</div>
                <div className="flex flex-wrap gap-1.5">
                  {EXP_OPTIONS.map((o) => (
                    <button key={o} onClick={() => toggle(exp, o, setExp)}
                      className={`text-xs px-2.5 py-1 rounded-full border transition cursor-pointer ${exp.includes(o) ? "bg-foreground text-background border-foreground" : "border-border hover:bg-muted text-foreground"}`}>
                      {o}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {filtered.length > 0 && (
              <div className="rounded-2xl bg-foreground text-background p-4 text-xs">
                <div className="font-display text-sm mb-1">Aria's pick today</div>
                <p className="text-background/70">{filtered[0].title} at {filtered[0].company} · {filtered[0].match}% match</p>
                <motion.div initial={{ width: 0 }} whileInView={{ width: `${filtered[0].match}%` }} viewport={{ once: true }} transition={{ duration: 1.2 }} className="mt-3 h-1 rounded-full bg-accent" />
              </div>
            )}
          </aside>

          <Stagger className="space-y-3">
            {filtered.map((j) => (
              <StaggerItem key={j.id}><JobCard job={j} onAutoApply={setSelectedJobForApply} /></StaggerItem>
            ))}
            {filtered.length === 0 && (
              <div className="rounded-2xl border border-dashed border-border bg-card p-12 text-center text-muted-foreground">
                <div className="font-display text-lg text-foreground">
                  {jobs.length === 0 ? "No jobs discovered yet" : "No matches found"}
                </div>
                <p className="text-sm mt-1">
                  {jobs.length === 0
                    ? "Start a new search to discover roles matching your profile."
                    : "Try removing a filter or widening your search query."}
                </p>
              </div>
            )}
          </Stagger>
        </div>
      )}
      <ApplyDialog
        job={selectedJobForApply}
        runId={activeRunId || localStorage.getItem("aria.active_run_id") || null}
        onClose={() => setSelectedJobForApply(null)}
      />
    </>
  );
}

