import { AnimatedCounter } from "../motion/counter";
import { Stagger, StaggerItem } from "../motion/primitives";

const stats = [
  { label: "Jobs discovered", value: 1248320, suffix: "+" },
  { label: "Applications submitted", value: 84210, suffix: "+" },
  { label: "Interviews generated", value: 9612, suffix: "" },
  { label: "Companies reached", value: 4180, suffix: "" },
];

export function TrustSection() {
  return (
    <section id="trust" className="px-6 py-24 border-y border-border bg-muted/40">
      <div className="mx-auto max-w-6xl">
        <p className="text-sm uppercase tracking-[0.18em] text-muted-foreground text-center">
          Aria at work, every minute
        </p>
        <Stagger className="mt-10 grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-12">
          {stats.map((s) => (
            <StaggerItem key={s.label} className="text-center">
              <div className="font-display text-[clamp(2.2rem,4vw,3.4rem)] tracking-tight text-foreground">
                <AnimatedCounter value={s.value} />
                <span className="text-accent">{s.suffix}</span>
              </div>
              <div className="mt-2 text-sm text-muted-foreground">{s.label}</div>
            </StaggerItem>
          ))}
        </Stagger>
      </div>
    </section>
  );
}
