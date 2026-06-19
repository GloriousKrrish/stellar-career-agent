import { FileText, ScanLine, Search, Target, Send, LineChart } from "lucide-react";
import { Stagger, StaggerItem } from "../motion/primitives";

const steps = [
  { icon: FileText, title: "Upload resume", body: "Drag, drop, done. Aria reads it in seconds." },
  { icon: ScanLine, title: "Extract skills", body: "Skills, signals and seniority — modeled with care." },
  { icon: Search, title: "Search jobs", body: "Continuously crawl 40+ sources across the web." },
  { icon: Target, title: "Match opportunities", body: "Multi-factor scoring against your goals." },
  { icon: Send, title: "Apply or hand off", body: "Auto-apply or wait for your green light." },
  { icon: LineChart, title: "Track everything", body: "One pipeline, every stage, in real time." },
];

export function Workflow() {
  return (
    <section id="workflow" className="px-6 py-28">
      <div className="mx-auto max-w-6xl">
        <div className="max-w-2xl">
          <p className="text-sm uppercase tracking-[0.18em] text-accent">How the agents work</p>
          <h2 className="mt-3 font-display text-4xl md:text-5xl tracking-tight">
            Six specialists. One thoughtful career.
          </h2>
          <p className="mt-4 text-muted-foreground text-lg">
            Each agent does one thing exceptionally well. Together they replace the most exhausting parts of job searching.
          </p>
        </div>

        <Stagger className="mt-16 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px bg-border rounded-3xl overflow-hidden border border-border">
          {steps.map((s, i) => (
            <StaggerItem key={s.title} className="bg-background p-8 group hover:bg-card transition-colors">
              <div className="flex items-start justify-between">
                <div className="h-11 w-11 rounded-xl bg-muted flex items-center justify-center group-hover:bg-secondary transition-colors">
                  <s.icon className="h-5 w-5 text-accent" />
                </div>
                <span className="font-display text-sm text-muted-foreground tabular-nums">0{i + 1}</span>
              </div>
              <h3 className="mt-6 font-display text-xl">{s.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{s.body}</p>
            </StaggerItem>
          ))}
        </Stagger>
      </div>
    </section>
  );
}
