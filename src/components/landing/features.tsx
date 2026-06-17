import { FadeIn } from "../motion/primitives";

export function FeatureSplits() {
  return (
    <section className="px-6 py-28 bg-muted/40 border-y border-border">
      <div className="mx-auto max-w-6xl space-y-32">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <FadeIn>
            <p className="text-sm uppercase tracking-[0.18em] text-accent">Resume intelligence</p>
            <h2 className="mt-3 font-display text-4xl tracking-tight">
              A resume that thinks for itself.
            </h2>
            <p className="mt-4 text-muted-foreground text-lg">
              Aria extracts your skills, scores ATS compatibility and surfaces the gaps standing between you and the next role.
            </p>
            <ul className="mt-6 space-y-3 text-sm text-foreground/80">
              {["ATS readiness score with rationale", "Skill gap analysis with study paths", "Tailored variants per application"].map((t) => (
                <li key={t} className="flex items-start gap-3">
                  <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-accent" />
                  {t}
                </li>
              ))}
            </ul>
          </FadeIn>
          <FadeIn delay={0.1}>
            <div className="rounded-3xl border border-border bg-card shadow-elegant p-8">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <div className="text-xs text-muted-foreground">Resume strength</div>
                  <div className="font-display text-4xl mt-1">86<span className="text-muted-foreground text-2xl">/100</span></div>
                </div>
                <div className="h-20 w-20 relative">
                  <svg viewBox="0 0 80 80" className="h-full w-full -rotate-90">
                    <circle cx="40" cy="40" r="34" stroke="oklch(0.91 0.012 75)" strokeWidth="6" fill="none" />
                    <circle cx="40" cy="40" r="34" stroke="oklch(0.62 0.07 55)" strokeWidth="6" fill="none"
                      strokeDasharray={2 * Math.PI * 34}
                      strokeDashoffset={2 * Math.PI * 34 * (1 - 0.86)}
                      strokeLinecap="round" />
                  </svg>
                </div>
              </div>
              <div className="space-y-3">
                {[
                  { label: "ATS compatibility", v: 92 },
                  { label: "Skill clarity", v: 88 },
                  { label: "Impact statements", v: 74 },
                ].map((m) => (
                  <div key={m.label}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-muted-foreground">{m.label}</span>
                      <span className="tabular-nums">{m.v}%</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                      <div className="h-full bg-accent" style={{ width: `${m.v}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </FadeIn>
        </div>

        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <FadeIn className="lg:order-2">
            <p className="text-sm uppercase tracking-[0.18em] text-accent">Auto Apply</p>
            <h2 className="mt-3 font-display text-4xl tracking-tight">
              Applications, drafted with taste.
            </h2>
            <p className="mt-4 text-muted-foreground text-lg">
              Tailored cover letters, accurate forms, and a one-click approval queue — so every application sounds like the best version of you.
            </p>
            <ul className="mt-6 space-y-3 text-sm text-foreground/80">
              {["Per-role tailoring with editable drafts", "Smart deduplication across job boards", "Pause, edit or approve in a single keystroke"].map((t) => (
                <li key={t} className="flex items-start gap-3">
                  <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-accent" />
                  {t}
                </li>
              ))}
            </ul>
          </FadeIn>
          <FadeIn delay={0.1} className="lg:order-1">
            <div className="rounded-3xl border border-border bg-card shadow-elegant p-6">
              {["Searching", "Analyzing", "Matching", "Applying", "Awaiting you", "Completed"].map((stage, i) => (
                <div key={stage} className="flex items-center gap-4 py-3 border-b border-border last:border-0">
                  <div className="h-7 w-7 rounded-full bg-muted flex items-center justify-center text-xs font-display">{i + 1}</div>
                  <div className="flex-1">
                    <div className="text-sm font-medium">{stage}</div>
                    <div className="text-xs text-muted-foreground">{[312, 287, 142, 14, 3, 89][i]} roles</div>
                  </div>
                  <div className="h-1.5 w-24 bg-muted rounded-full overflow-hidden">
                    <div className="h-full bg-accent" style={{ width: `${[100, 88, 64, 22, 100, 100][i]}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </FadeIn>
        </div>
      </div>
    </section>
  );
}
