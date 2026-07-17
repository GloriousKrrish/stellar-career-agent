"use client";
import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { CheckCircle2, Plus, AlertCircle, Info, Chrome, Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import { PageHeader } from "@/components/shell/sidebar";
import { CONNECTIONS } from "@/lib/mock/user";
import { getCurrentUser } from "@/lib/auth";
import { api } from "@/lib/api";

export const Route = createFileRoute("/app/settings")({
  head: () => ({
    meta: [
      { title: "Settings — Aria" },
      { name: "description", content: "Profile, notifications, privacy, integrations and browser automation settings." },
    ],
  }),
  component: SettingsPage,
});

const sections = ["Profile", "Notifications", "Privacy", "Connected Platforms", "Browser Automation"] as const;

function Toggle({ 
  defaultOn = true, 
  value, 
  onChange, 
  disabled 
}: { 
  defaultOn?: boolean; 
  value?: boolean; 
  onChange?: (val: boolean) => void;
  disabled?: boolean;
}) {
  const [internalOn, setInternalOn] = useState(defaultOn);
  const on = value !== undefined ? value : internalOn;

  const handleToggle = () => {
    if (disabled) return;
    if (value === undefined) {
      setInternalOn(!on);
    }
    if (onChange) {
      onChange(!on);
    }
  };

  return (
    <button 
      onClick={handleToggle} 
      disabled={disabled}
      className={`w-10 h-6 rounded-full p-0.5 transition-colors ${on ? "bg-accent" : "bg-muted"} ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
    >
      <motion.div layout className="h-5 w-5 rounded-full bg-background shadow" style={{ marginLeft: on ? 16 : 0 }} />
    </button>
  );
}

function SettingsPage() {
  const [section, setSection] = useState<typeof sections[number]>("Profile");
  const [connections, setConnections] = useState(CONNECTIONS);

  // Browser Automation States
  const [browserMode, setBrowserMode] = useState<"production" | "development">("production");
  const [executablePath, setExecutablePath] = useState("");
  const [profilePath, setProfilePath] = useState("");
  const [keepOpen, setKeepOpen] = useState(false);
  const [debugLogging, setDebugLogging] = useState(false);
  const [headless, setHeadless] = useState(false);
  const [slowMo, setSlowMo] = useState(1200);
  
  const [effectiveProfilePath, setEffectiveProfilePath] = useState("");
  const [loadingSettings, setLoadingSettings] = useState(false);
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Platform sessions state
  const [sessions, setSessions] = useState<Array<{
    platform: string;
    status: "active" | "expired" | "none";
    saved_at: string | null;
    expires_hint: string | null;
    applications_count: number;
    cookie_count: number;
  }>>([]);
  const [loadingSessions, setLoadingSessions] = useState(false);

  const [profileName, setProfileName] = useState("");
  const [profileTitle, setProfileTitle] = useState("");
  const [profileLocation, setProfileLocation] = useState("");
  const [profileSkills, setProfileSkills] = useState<string[]>([]);
  const [profileExperience, setProfileExperience] = useState<any[]>([]);
  const [newSkillText, setNewSkillText] = useState("");
  const [postText, setPostText] = useState("");
  const [parsingPost, setParsingPost] = useState(false);
  const [profileSaving, setProfileSaving] = useState(false);

  const user = getCurrentUser() || {
    name: "Job Seeker",
    email: "",
    title: "Software Engineer",
    location: "Remote",
  };

  useEffect(() => {
    const activeUser = getCurrentUser();
    if (activeUser) {
      setProfileName(activeUser.name || "");
      setProfileTitle(activeUser.title || "");
      setProfileLocation(activeUser.location || "");
      setProfileSkills(activeUser.skills || []);
      setProfileExperience(activeUser.experience || []);
    }
  }, []);

  const handleSaveProfile = async () => {
    setProfileSaving(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const updated = await api.updateProfile({
        name: profileName,
        title: profileTitle,
        location: profileLocation,
        skills: profileSkills,
        experience: profileExperience,
      });
      setSuccessMsg("Profile saved successfully!");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to save profile.");
    } finally {
      setProfileSaving(false);
    }
  };

  const handleParsePost = async () => {
    if (!postText.trim()) return;
    setParsingPost(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const parsed = await api.parseExperience(postText);
      if (parsed.experience_entry) {
        setProfileExperience((prev) => [...prev, parsed.experience_entry]);
      }
      if (parsed.skills && parsed.skills.length > 0) {
        setProfileSkills((prev) => {
          const merged = [...prev];
          parsed.skills.forEach((s) => {
            if (!merged.includes(s)) merged.push(s);
          });
          return merged;
        });
      }
      setSuccessMsg("Successfully parsed internship/work experience post and added to your profile!");
      setPostText("");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to parse experience post.");
    } finally {
      setParsingPost(false);
    }
  };

  const initials = user.name
    ? user.name.split(" ").map((n: string) => n[0]).join("").toUpperCase().slice(0, 2)
    : "JS";

  // Load browser settings and active sessions from backend
  useEffect(() => {
    if (section === "Browser Automation") {
      loadBrowserSettings();
      loadSessions();
    }
  }, [section]);

  const loadBrowserSettings = async () => {
    setLoadingSettings(true);
    setErrorMsg(null);
    try {
      const data = await api.getBrowserSettings();
      setBrowserMode(data.mode as any);
      setExecutablePath(data.browser_executable_path || "");
      setProfilePath(data.profile_path || "");
      setKeepOpen(data.keep_open);
      setDebugLogging(data.debug_logging);
      setHeadless(data.headless);
      setSlowMo(data.slow_mo);
      setEffectiveProfilePath(data.effective_profile_path || "");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load browser automation settings.");
    } finally {
      setLoadingSettings(false);
    }
  };

  const loadSessions = async () => {
    setLoadingSessions(true);
    try {
      const data = await api.getSessions();
      setSessions(data.sessions || []);
    } catch (err) {
      console.error("Failed to load platform sessions", err);
    } finally {
      setLoadingSessions(false);
    }
  };

  const handleClearSession = async (platform: string) => {
    if (!confirm(`Are you sure you want to clear the saved login session for ${platform}?`)) {
      return;
    }
    try {
      await api.clearSession(platform);
      setSuccessMsg(`Session for ${platform} cleared successfully.`);
      loadSessions();
    } catch (err: any) {
      setErrorMsg(err.message || `Failed to clear session for ${platform}.`);
    }
  };

  const saveSettings = async () => {
    setSaving(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const result = await api.updateBrowserSettings({
        mode: browserMode,
        browser_executable_path: executablePath.trim() || undefined,
        profile_path: profilePath.trim() || undefined,
        keep_open: keepOpen,
        debug_logging: debugLogging,
        headless: headless,
        slow_mo: slowMo,
      });
      setSuccessMsg(result.message || "Browser automation settings saved successfully.");
      if (result.config) {
        setEffectiveProfilePath(result.config.effective_profile_path || "");
        // If mode changed to development, sync the keepOpen toggle value
        if (result.config.mode === "development") {
          setKeepOpen(true);
        }
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to save browser settings.");
    } finally {
      setSaving(false);
    }
  };

  // Sync keepOpen / headless states when browserMode switches
  useEffect(() => {
    if (browserMode === "development") {
      setKeepOpen(true);
      setHeadless(false);
    }
  }, [browserMode]);

  return (
    <>
      <PageHeader title="Settings" subtitle="Aria works the way you want it to." />
      <div className="grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-8">
        <nav className="space-y-1">
          {sections.map((s) => (
            <button
              key={s}
              onClick={() => setSection(s)}
              className={`block w-full text-left px-3 py-2 rounded-xl text-sm transition-colors ${section === s ? "bg-card border border-border shadow-soft" : "text-muted-foreground hover:text-foreground hover:bg-muted/60"}`}
            >
              {s}
            </button>
          ))}
        </nav>

        <div className="space-y-4">
          {section === "Profile" && (
            <div className="space-y-6">
              {/* Profile Details Card */}
              <div className="rounded-2xl border border-border bg-card p-6 shadow-soft space-y-5">
                <div className="flex items-center gap-4">
                  <div className="h-16 w-16 rounded-full bg-foreground text-background flex items-center justify-center font-display text-xl">{initials}</div>
                  <div>
                    <div className="font-display text-lg">{profileName || "Job Seeker"}</div>
                    <div className="text-xs text-muted-foreground">{profileTitle || "Software Engineer"} · {profileLocation || "Remote"}</div>
                  </div>
                </div>

                {errorMsg && (
                  <div className="p-3 bg-red-500/15 border border-red-500/20 rounded-xl flex gap-2 text-red-200 text-xs">
                    <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                    <div>{errorMsg}</div>
                  </div>
                )}

                {successMsg && (
                  <div className="p-3 bg-emerald-500/15 border border-emerald-500/20 rounded-xl flex gap-2 text-emerald-200 text-xs">
                    <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
                    <div>{successMsg}</div>
                  </div>
                )}

                <div className="grid sm:grid-cols-2 gap-4">
                  <label className="block">
                    <span className="text-xs text-muted-foreground">Full name</span>
                    <input 
                      value={profileName} 
                      onChange={(e) => setProfileName(e.target.value)}
                      className="mt-1.5 w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent" 
                    />
                  </label>
                  <label className="block">
                    <span className="text-xs text-muted-foreground">Email (read-only)</span>
                    <input 
                      value={user.email} 
                      disabled
                      className="mt-1.5 w-full rounded-xl border border-border bg-muted/50 px-3 py-2 text-sm outline-none cursor-not-allowed" 
                    />
                  </label>
                  <label className="block">
                    <span className="text-xs text-muted-foreground">Title</span>
                    <input 
                      value={profileTitle} 
                      onChange={(e) => setProfileTitle(e.target.value)}
                      className="mt-1.5 w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent" 
                    />
                  </label>
                  <label className="block">
                    <span className="text-xs text-muted-foreground">Location</span>
                    <input 
                      value={profileLocation} 
                      onChange={(e) => setProfileLocation(e.target.value)}
                      className="mt-1.5 w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent" 
                    />
                  </label>
                </div>
              </div>

              {/* Quick AI Experience Parser Card */}
              <div className="rounded-2xl border border-border bg-card p-6 shadow-soft space-y-4">
                <div>
                  <h3 className="text-sm font-semibold text-foreground">AI Quick-Parse Work Experience</h3>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Paste a LinkedIn post, internship description, or resume snippet to automatically parse and structure it using Gemini.
                  </p>
                </div>
                <textarea
                  value={postText}
                  onChange={(e) => setPostText(e.target.value)}
                  placeholder="e.g. Completed my 3-month internship at YOJAK NGO, Nigdi... worked on Student scholarship management and documentation..."
                  rows={4}
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent resize-none"
                />
                <div className="flex justify-end">
                  <button
                    onClick={handleParsePost}
                    disabled={parsingPost || !postText.trim()}
                    className="rounded-xl bg-accent text-accent-foreground font-medium text-xs px-4 py-2 hover:opacity-90 transition-opacity flex items-center gap-1.5"
                  >
                    {parsingPost && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                    Parse & Add Experience
                  </button>
                </div>
              </div>

              {/* Skills Card */}
              <div className="rounded-2xl border border-border bg-card p-6 shadow-soft space-y-4">
                <h3 className="text-sm font-semibold text-foreground">Skills</h3>
                <div className="flex flex-wrap gap-2">
                  {profileSkills.map((s, idx) => (
                    <span 
                      key={s + idx} 
                      className="inline-flex items-center gap-1 bg-muted px-2.5 py-1 rounded-full text-xs font-medium text-muted-foreground"
                    >
                      {s}
                      <button 
                        onClick={() => setProfileSkills((prev) => prev.filter((_, i) => i !== idx))}
                        className="hover:text-foreground text-[10px]"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                  {profileSkills.length === 0 && (
                    <span className="text-xs text-muted-foreground">No skills added yet.</span>
                  )}
                </div>
                <div className="flex gap-2">
                  <input
                    value={newSkillText}
                    onChange={(e) => setNewSkillText(e.target.value)}
                    placeholder="Add a skill"
                    className="flex-1 rounded-xl border border-border bg-background px-3 py-1.5 text-xs outline-none focus:border-accent"
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && newSkillText.trim()) {
                        if (!profileSkills.includes(newSkillText.trim())) {
                          setProfileSkills([...profileSkills, newSkillText.trim()]);
                        }
                        setNewSkillText("");
                      }
                    }}
                  />
                  <button
                    onClick={() => {
                      if (newSkillText.trim()) {
                        if (!profileSkills.includes(newSkillText.trim())) {
                          setProfileSkills([...profileSkills, newSkillText.trim()]);
                        }
                        setNewSkillText("");
                      }
                    }}
                    className="rounded-xl border border-border text-xs px-3 py-1.5 hover:bg-muted font-medium"
                  >
                    Add
                  </button>
                </div>
              </div>

              {/* Work Experience Card */}
              <div className="rounded-2xl border border-border bg-card p-6 shadow-soft space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-foreground">Work Experience</h3>
                  <button
                    onClick={() => setProfileExperience([...profileExperience, {
                      title: "New Role",
                      company: "Company Name",
                      start_date: "Month Year",
                      end_date: "Month Year",
                      description: "",
                      achievements: []
                    }])}
                    className="rounded-xl border border-border text-[11px] px-2.5 py-1 hover:bg-muted font-medium flex items-center gap-1"
                  >
                    <Plus className="h-3 w-3" /> Add Manually
                  </button>
                </div>

                <div className="space-y-4 divide-y divide-border/60">
                  {profileExperience.map((exp, idx) => (
                    <div key={idx} className="pt-4 first:pt-0 space-y-3">
                      <div className="flex items-start justify-between gap-4">
                        <div className="grid sm:grid-cols-2 gap-3 flex-1">
                          <label className="block">
                            <span className="text-[10px] text-muted-foreground">Job Title</span>
                            <input
                              value={exp.title || ""}
                              onChange={(e) => {
                                const next = [...profileExperience];
                                next[idx].title = e.target.value;
                                setProfileExperience(next);
                              }}
                              className="mt-1 w-full rounded-lg border border-border bg-background px-2.5 py-1 text-xs outline-none focus:border-accent"
                            />
                          </label>
                          <label className="block">
                            <span className="text-[10px] text-muted-foreground">Company</span>
                            <input
                              value={exp.company || ""}
                              onChange={(e) => {
                                const next = [...profileExperience];
                                next[idx].company = e.target.value;
                                setProfileExperience(next);
                              }}
                              className="mt-1 w-full rounded-lg border border-border bg-background px-2.5 py-1 text-xs outline-none focus:border-accent"
                            />
                          </label>
                          <label className="block">
                            <span className="text-[10px] text-muted-foreground">Start Date</span>
                            <input
                              value={exp.start_date || ""}
                              onChange={(e) => {
                                const next = [...profileExperience];
                                next[idx].start_date = e.target.value;
                                setProfileExperience(next);
                              }}
                              className="mt-1 w-full rounded-lg border border-border bg-background px-2.5 py-1 text-xs outline-none focus:border-accent"
                            />
                          </label>
                          <label className="block">
                            <span className="text-[10px] text-muted-foreground">End Date</span>
                            <input
                              value={exp.end_date || ""}
                              onChange={(e) => {
                                const next = [...profileExperience];
                                next[idx].end_date = e.target.value;
                                setProfileExperience(next);
                              }}
                              className="mt-1 w-full rounded-lg border border-border bg-background px-2.5 py-1 text-xs outline-none focus:border-accent"
                            />
                          </label>
                        </div>
                        <button
                          onClick={() => setProfileExperience((prev) => prev.filter((_, i) => i !== idx))}
                          className="text-red-400 hover:text-red-300 text-xs font-medium mt-6 font-semibold"
                        >
                          Remove
                        </button>
                      </div>

                      <label className="block">
                        <span className="text-[10px] text-muted-foreground">Description</span>
                        <textarea
                          value={exp.description || ""}
                          onChange={(e) => {
                            const next = [...profileExperience];
                            next[idx].description = e.target.value;
                            setProfileExperience(next);
                          }}
                          rows={2}
                          className="mt-1 w-full rounded-lg border border-border bg-background px-2.5 py-1 text-xs outline-none focus:border-accent resize-none"
                        />
                      </label>

                      {/* Achievements list */}
                      <div className="space-y-1.5">
                        <span className="text-[10px] text-muted-foreground block">Key Achievements & Responsibilities</span>
                        {(exp.achievements || []).map((ach: string, achIdx: number) => (
                          <div key={achIdx} className="flex gap-2 items-center">
                            <input
                              value={ach}
                              onChange={(e) => {
                                const next = [...profileExperience];
                                next[idx].achievements[achIdx] = e.target.value;
                                setProfileExperience(next);
                              }}
                              className="flex-1 rounded-lg border border-border bg-background px-2.5 py-1 text-xs outline-none focus:border-accent"
                            />
                            <button
                              onClick={() => {
                                const next = [...profileExperience];
                                next[idx].achievements = next[idx].achievements.filter((_: any, i: number) => i !== achIdx);
                                setProfileExperience(next);
                              }}
                              className="text-muted-foreground hover:text-foreground text-xs"
                            >
                              ×
                            </button>
                          </div>
                        ))}
                        <button
                          onClick={() => {
                            const next = [...profileExperience];
                            if (!next[idx].achievements) next[idx].achievements = [];
                            next[idx].achievements.push("");
                            setProfileExperience(next);
                          }}
                          className="text-[10px] text-accent hover:underline font-medium"
                        >
                          + Add Achievement
                        </button>
                      </div>
                    </div>
                  ))}

                  {profileExperience.length === 0 && (
                    <div className="text-center py-4 text-xs text-muted-foreground">
                      No work experiences added yet. Try pasting your experience post above!
                    </div>
                  )}
                </div>
              </div>

              {/* Save All Profile Changes */}
              <div className="flex justify-end pt-2">
                <button
                  onClick={handleSaveProfile}
                  disabled={profileSaving}
                  className="rounded-xl bg-foreground text-background font-medium text-xs px-6 py-2.5 hover:opacity-90 transition-opacity flex items-center gap-2"
                >
                  {profileSaving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  Save All Profile Changes
                </button>
              </div>
            </div>
          )}

          {section === "Notifications" && (
            <div className="rounded-2xl border border-border bg-card p-6 shadow-soft divide-y divide-border">
              {[
                ["New matches above 90%", "Email instantly when Aria finds a top match"],
                ["Daily digest", "Morning summary of your agents' overnight work"],
                ["Interview reminders", "30 min before each scheduled interview"],
                ["Weekly insights", "Performance trends and recommendations"],
              ].map(([t, s], i) => (
                <div key={t} className="flex items-center justify-between py-4 first:pt-0 last:pb-0">
                  <div>
                    <div className="text-sm font-medium">{t}</div>
                    <div className="text-xs text-muted-foreground">{s}</div>
                  </div>
                  <Toggle defaultOn={i !== 2} />
                </div>
              ))}
            </div>
          )}

          {section === "Privacy" && (
            <div className="rounded-2xl border border-border bg-card p-6 shadow-soft divide-y divide-border">
              {[
                ["Discoverable to recruiters", "Allow vetted recruiters to find your anonymous profile"],
                ["Anonymous mode for current employer", "Hide your profile from your current company"],
                ["Share analytics with Aria", "Help us improve matching by contributing anonymized data"],
              ].map(([t, s], i) => (
                <div key={t} className="flex items-center justify-between py-4 first:pt-0 last:pb-0">
                  <div>
                    <div className="text-sm font-medium">{t}</div>
                    <div className="text-xs text-muted-foreground">{s}</div>
                  </div>
                  <Toggle defaultOn={i !== 0} />
                </div>
              ))}
            </div>
          )}

          {section === "Connected Platforms" && (
            <div className="grid sm:grid-cols-2 gap-3">
              {connections.map((c) => (
                <div key={c.id} className="rounded-2xl border border-border bg-card p-5 shadow-soft">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-xl bg-muted flex items-center justify-center font-display text-sm">{c.name[0]}</div>
                      <div>
                        <div className="font-medium text-sm">{c.name}</div>
                        <div className="text-xs text-muted-foreground">{c.description}</div>
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => setConnections((cs) => cs.map((x) => x.id === c.id ? { ...x, connected: !x.connected } : x))}
                    className={`mt-4 w-full rounded-xl text-xs px-3 py-2 transition-colors inline-flex items-center justify-center gap-1.5 ${
                      c.connected ? "bg-muted text-foreground" : "bg-foreground text-background hover:opacity-90"
                    }`}
                  >
                    {c.connected ? <><CheckCircle2 className="h-3.5 w-3.5 text-accent" /> Connected</> : <><Plus className="h-3.5 w-3.5" /> Connect</>}
                  </button>
                </div>
              ))}
            </div>
          )}

          {section === "Browser Automation" && (
            <div className="rounded-2xl border border-border bg-card p-6 shadow-soft space-y-6">
              <div>
                <h3 className="text-lg font-display font-semibold flex items-center gap-2 text-foreground">
                  <Chrome className="h-5 w-5 text-accent" />
                  Browser Automation Settings
                </h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Configure browser profiles and execution settings for the autonomous job application engine.
                </p>
              </div>

              {loadingSettings ? (
                <div className="flex items-center justify-center py-10">
                  <Loader2 className="h-8 w-8 animate-spin text-accent" />
                  <span className="ml-2 text-sm text-muted-foreground">Loading settings...</span>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Mode Alert Banner */}
                  <div className={`p-4 rounded-xl border flex gap-3 ${
                    browserMode === "development" 
                      ? "bg-amber-500/10 border-amber-500/20 text-amber-200" 
                      : "bg-blue-500/10 border-blue-500/20 text-blue-200"
                  }`}>
                    <Info className="h-5 w-5 shrink-0 mt-0.5" />
                    <div>
                      <div className="font-semibold text-sm">
                        {browserMode === "development" ? "Development Mode Active" : "Production Mode Active"}
                      </div>
                      <div className="text-xs opacity-90 mt-1">
                        {browserMode === "development" 
                          ? `Reuses active login sessions and leaves browser open. Resolved path: ${effectiveProfilePath || "Using Default Sub-profile"}`
                          : "Launches isolated context for each application. Closes automatically on completion."}
                      </div>
                    </div>
                  </div>

                  {errorMsg && (
                    <div className="p-3 bg-red-500/15 border border-red-500/20 rounded-xl flex gap-2 text-red-200 text-xs">
                      <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                      <div>{errorMsg}</div>
                    </div>
                  )}

                  {successMsg && (
                    <div className="p-3 bg-emerald-500/15 border border-emerald-500/20 rounded-xl flex gap-2 text-emerald-200 text-xs">
                      <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
                      <div>{successMsg}</div>
                    </div>
                  )}

                  <div className="grid sm:grid-cols-2 gap-5">
                    {/* Browser Mode */}
                    <div className="space-y-2">
                      <label className="block text-xs font-medium text-muted-foreground">Browser Automation Mode</label>
                      <select 
                        value={browserMode}
                        onChange={(e) => setBrowserMode(e.target.value as any)}
                        className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent"
                      >
                        <option value="production">Production Mode (Isolated Context)</option>
                        <option value="development">Development Mode (Persistent User Profile)</option>
                      </select>
                    </div>

                    {/* Executable Path */}
                    <div className="space-y-2">
                      <label className="block text-xs font-medium text-muted-foreground">Browser Executable Path (Optional)</label>
                      <input 
                        type="text" 
                        value={executablePath}
                        onChange={(e) => setExecutablePath(e.target.value)}
                        placeholder="Default Playwright Chromium"
                        className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent"
                      />
                      <span className="text-[10px] text-muted-foreground block">
                        Leave blank to use default built-in browser instance.
                      </span>
                    </div>

                    {/* Profile Path */}
                    <div className="space-y-2 sm:col-span-2">
                      <label className="block text-xs font-medium text-muted-foreground">Chrome Profile Data Directory</label>
                      <input 
                        type="text" 
                        value={profilePath}
                        onChange={(e) => setProfilePath(e.target.value)}
                        placeholder="e.g. C:\Users\YourUser\AppData\Local\Google\Chrome\User Data\StellarProfile"
                        className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent"
                      />
                      <span className="text-[10px] text-muted-foreground block">
                        Path to Chrome user data directory. In development mode, session cookies will be preserved here.
                      </span>
                    </div>

                    {/* Slow-mo */}
                    <div className="space-y-2">
                      <label className="block text-xs font-medium text-muted-foreground">Slow-mo Pacing (ms)</label>
                      <input 
                        type="number" 
                        value={slowMo}
                        onChange={(e) => setSlowMo(parseInt(e.target.value) || 0)}
                        placeholder="1200"
                        className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent"
                      />
                      <span className="text-[10px] text-muted-foreground block">
                        Delay between actions to look human.
                      </span>
                    </div>

                    {/* Headless Checkbox */}
                    <div className="space-y-2 flex flex-col justify-end">
                      <div className="flex items-center gap-3 p-1">
                        <input 
                          type="checkbox" 
                          id="headless"
                          checked={headless}
                          onChange={(e) => setHeadless(e.target.checked)}
                          disabled={browserMode === "development"}
                          className="h-4 w-4 rounded border-border bg-background accent-accent"
                        />
                        <label htmlFor="headless" className="text-xs font-medium select-none cursor-pointer text-muted-foreground">
                          Run Headless (no browser window)
                        </label>
                      </div>
                      <span className="text-[10px] text-muted-foreground block ml-7">
                        {browserMode === "development" ? "Headless is disabled in Development Mode." : "Run browser invisibly in the background."}
                      </span>
                    </div>
                  </div>

                  <hr className="border-border" />

                  {/* Toggles */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm font-medium">Keep Browser Open</div>
                        <div className="text-xs text-muted-foreground">Prevent browser window from closing after application completion.</div>
                      </div>
                      <Toggle 
                        value={keepOpen} 
                        onChange={(on) => setKeepOpen(on)}
                        disabled={browserMode === "development"}
                      />
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm font-medium">Debug Logging</div>
                        <div className="text-xs text-muted-foreground">Stream detailed automation actions to the WebSocket progress log.</div>
                      </div>
                      <Toggle 
                        value={debugLogging} 
                        onChange={(on) => setDebugLogging(on)}
                      />
                    </div>
                  </div>

                  <div className="pt-2 flex justify-end">
                    <button
                      onClick={saveSettings}
                      disabled={saving}
                      className="rounded-xl bg-foreground text-background font-medium text-xs px-4 py-2 hover:opacity-90 transition-opacity flex items-center gap-2"
                    >
                      {saving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                      Save Browser Settings
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Session Manager Dashboard */}
          {section === "Browser Automation" && (
            <div className="rounded-2xl border border-border bg-card p-6 shadow-soft space-y-6">
              <div>
                <h3 className="text-lg font-display font-semibold flex items-center gap-2 text-foreground">
                  <CheckCircle2 className="h-5 w-5 text-accent" />
                  Saved Platform Sessions
                </h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Manage persistent login sessions and cookies cached by Human-in-the-Loop automation.
                </p>
              </div>

              {loadingSessions ? (
                <div className="flex items-center justify-center py-6">
                  <Loader2 className="h-6 w-6 animate-spin text-accent" />
                  <span className="ml-2 text-xs text-muted-foreground">Loading active sessions...</span>
                </div>
              ) : sessions.length === 0 ? (
                <div className="text-center py-6 text-xs text-muted-foreground">
                  No login sessions saved yet. Run browser automation to capture and persist sessions.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-border/60 text-muted-foreground font-semibold">
                        <th className="py-2.5">Platform</th>
                        <th className="py-2.5">Status</th>
                        <th className="py-2.5">Saved At</th>
                        <th className="py-2.5">Applications</th>
                        <th className="py-2.5">Cookies</th>
                        <th className="py-2.5 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/40">
                      {sessions.map((s) => (
                        <tr key={s.platform} className="hover:bg-muted/15 transition-colors">
                          <td className="py-3 font-medium capitalize flex items-center gap-2">
                            <span className="h-1.5 w-1.5 rounded-full bg-accent" />
                            {s.platform}
                          </td>
                          <td className="py-3">
                            {s.status === "active" && (
                              <span className="bg-emerald-500/10 text-emerald-400 font-semibold px-2 py-0.5 rounded-md text-[10px]">
                                Logged In / Active
                              </span>
                            )}
                            {s.status === "expired" && (
                              <span className="bg-amber-500/10 text-amber-400 font-semibold px-2 py-0.5 rounded-md text-[10px]">
                                Session Expired
                              </span>
                            )}
                            {s.status === "none" && (
                              <span className="bg-neutral-800 text-muted-foreground px-2 py-0.5 rounded-md text-[10px]">
                                No Session
                              </span>
                            )}
                          </td>
                          <td className="py-3 text-muted-foreground">
                            {s.saved_at ? new Date(s.saved_at).toLocaleString() : "Never"}
                          </td>
                          <td className="py-3 font-semibold text-foreground/90">
                            {s.applications_count} submitted
                          </td>
                          <td className="py-3 text-muted-foreground">
                            {s.cookie_count} cookies cached
                          </td>
                          <td className="py-3 text-right">
                            {s.status !== "none" && (
                              <button
                                onClick={() => handleClearSession(s.platform)}
                                className="text-red-400 hover:text-red-300 font-semibold hover:underline"
                              >
                                Clear Session
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function Field({ label, defaultValue }: { label: string; defaultValue: string }) {
  return (
    <label className="block">
      <span className="text-xs text-muted-foreground">{label}</span>
      <input defaultValue={defaultValue} className="mt-1.5 w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent" />
    </label>
  );
}
