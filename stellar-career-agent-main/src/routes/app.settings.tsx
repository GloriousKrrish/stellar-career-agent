"use client";
import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { CheckCircle2, Plus, Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import { PageHeader } from "@/components/shell/sidebar";
import { getMe } from "@/lib/api";

export const Route = createFileRoute("/app/settings")({
  head: () => ({
    meta: [
      { title: "Settings — Aria" },
      { name: "description", content: "Profile, notifications, privacy and integrations." },
    ],
  }),
  component: SettingsPage,
});

const sections = ["Profile", "Notifications", "Privacy", "Connected Platforms"] as const;

const MOCK_CONNECTIONS = [
  { id: "linkedin", name: "LinkedIn", description: "Import job preferences and networks.", connected: false },
  { id: "github", name: "GitHub", description: "Highlight open source contributions.", connected: false },
];

function Toggle({ defaultOn = true }: { defaultOn?: boolean }) {
  const [on, setOn] = useState(defaultOn);
  return (
    <button onClick={() => setOn(!on)} className={`w-10 h-6 rounded-full p-0.5 transition-colors ${on ? "bg-accent" : "bg-muted"}`}>
      <motion.div layout className="h-5 w-5 rounded-full bg-background shadow" style={{ marginLeft: on ? 16 : 0 }} />
    </button>
  );
}

function SettingsPage() {
  const [section, setSection] = useState<typeof sections[number]>("Profile");
  const [connections, setConnections] = useState(MOCK_CONNECTIONS);
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadUser() {
      try {
        const u = await getMe();
        setUser(u);
      } catch (_) {}
      setLoading(false);
    }
    loadUser();
  }, []);

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-accent" />
      </div>
    );
  }

  const initials = user?.name ? user.name.split(" ").map((n: string) => n[0]).join("").toUpperCase() : "U";

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
          {section === "Profile" && user && (
            <div className="rounded-2xl border border-border bg-card p-6 shadow-soft space-y-5">
              <div className="flex items-center gap-4">
                <div className="h-16 w-16 rounded-full bg-foreground text-background flex items-center justify-center font-display text-xl">{initials}</div>
                <div>
                  <div className="font-display text-lg">{user.name}</div>
                  <div className="text-xs text-muted-foreground">{user.title || "Applicant"} · {user.location || "Remote"}</div>
                </div>
              </div>
              <div className="grid sm:grid-cols-2 gap-4">
                <Field label="Full name" defaultValue={user.name} />
                <Field label="Email" defaultValue={user.email} />
                <Field label="Title" defaultValue={user.title || "Applicant"} />
                <Field label="Location" defaultValue={user.location || "Remote"} />
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
