"use client";
import { motion } from "framer-motion";
import { Link } from "@tanstack/react-router";
import { ArrowRight, Sparkles } from "lucide-react";
import { EASE } from "../motion/primitives";

function FloatingResume() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20, rotate: -2 }}
      animate={{ opacity: 1, y: 0, rotate: -2 }}
      transition={{ duration: 1, ease: EASE, delay: 0.4 }}
      className="absolute left-4 top-8 sm:left-12 sm:top-12 w-[240px] rounded-2xl bg-card border border-border shadow-elegant p-5"
    >
      <div className="flex items-center gap-3 mb-4">
        <div className="h-10 w-10 rounded-full bg-secondary flex items-center justify-center font-display text-secondary-foreground">AM</div>
        <div className="space-y-1">
          <div className="h-2.5 w-24 rounded bg-foreground/80" />
          <div className="h-2 w-16 rounded bg-muted-foreground/40" />
        </div>
      </div>
      <div className="space-y-2">
        {[100, 80, 90, 60, 75].map((w, i) => (
          <motion.div
            key={i}
            initial={{ scaleX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ duration: 0.6, delay: 0.7 + i * 0.08, ease: EASE }}
            style={{ width: `${w}%`, transformOrigin: "left" }}
            className="h-2 rounded bg-muted"
          />
        ))}
      </div>
      <div className="mt-4 flex gap-1.5">
        {["React", "TS", "Figma"].map((t) => (
          <span key={t} className="text-[10px] px-1.5 py-0.5 rounded-md bg-muted text-muted-foreground">{t}</span>
        ))}
      </div>
    </motion.div>
  );
}

function FloatingJobCard({ delay, x, y, company, role, match, accent }: { delay: number; x: number; y: number; company: string; role: string; match: number; accent?: boolean }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, delay, ease: EASE }}
      style={{ left: x, top: y }}
      className="absolute w-[220px] rounded-2xl bg-card border border-border shadow-elegant p-4"
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-foreground text-background font-display text-sm flex items-center justify-center">{company[0]}</div>
          <div>
            <div className="text-xs text-muted-foreground">{company}</div>
            <div className="text-sm font-medium leading-tight">{role}</div>
          </div>
        </div>
      </div>
      <div className="flex items-center justify-between">
        <div className={`text-xs font-medium ${accent ? "text-accent" : "text-muted-foreground"}`}>{match}% match</div>
        <div className="h-1.5 w-20 rounded-full bg-muted overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${match}%` }}
            transition={{ duration: 1.2, delay: delay + 0.3, ease: EASE }}
            className="h-full bg-accent"
          />
        </div>
      </div>
    </motion.div>
  );
}

function ConnectionLines() {
  return (
    <svg className="absolute inset-0 w-full h-full pointer-events-none" preserveAspectRatio="none">
      <defs>
        <linearGradient id="line" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="oklch(0.62 0.07 55)" stopOpacity="0.6" />
          <stop offset="100%" stopColor="oklch(0.62 0.07 55)" stopOpacity="0.05" />
        </linearGradient>
      </defs>
      {[
        "M 140 110 Q 240 130, 340 90",
        "M 140 140 Q 260 200, 360 240",
        "M 140 170 Q 300 270, 380 330",
      ].map((d, i) => (
        <motion.path
          key={i}
          d={d}
          fill="none"
          stroke="url(#line)"
          strokeWidth="1.2"
          strokeDasharray="4 4"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{ duration: 1.8, delay: 0.8 + i * 0.2, ease: EASE }}
        />
      ))}
    </svg>
  );
}

export function Hero() {
  return (
    <section className="relative pt-36 pb-24 px-6 overflow-hidden">
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 h-[600px] w-[1100px] rounded-full blur-3xl opacity-50"
             style={{ background: "radial-gradient(ellipse at center, oklch(0.85 0.04 65 / 0.5), transparent 70%)" }} />
      </div>

      <div className="mx-auto max-w-6xl grid lg:grid-cols-[1.1fr_1fr] gap-12 items-center">
        <div>
          <motion.div
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: EASE }}
            className="inline-flex items-center gap-2 rounded-full border border-border bg-card/60 backdrop-blur px-3 py-1 text-xs text-muted-foreground"
          >
            <Sparkles className="h-3.5 w-3.5 text-accent" />
            Now in private beta — first 500 careers
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, delay: 0.1, ease: EASE }}
            className="mt-5 font-display text-[clamp(2.5rem,6vw,4.75rem)] leading-[1.02] tracking-tight text-balance"
          >
            Your AI career agent finds jobs while you focus on your future.
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.25, ease: EASE }}
            className="mt-6 text-lg text-muted-foreground max-w-xl text-balance"
          >
            Upload your resume once and let intelligent agents discover, evaluate and help apply to the most relevant opportunities across the web.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.4, ease: EASE }}
            className="mt-8 flex flex-wrap items-center gap-3"
          >
            <Link
              to="/auth/register"
              className="group inline-flex items-center gap-2 rounded-full bg-foreground text-background px-6 py-3 text-sm font-medium hover:opacity-90 transition-opacity"
            >
              Start free search
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
            <a
              href="#workflow"
              className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-6 py-3 text-sm font-medium hover:bg-muted transition-colors"
            >
              See how it works
            </a>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.7 }}
            className="mt-10 flex items-center gap-3 text-xs text-muted-foreground"
          >
            <div className="flex -space-x-2">
              {["A", "S", "K", "L"].map((c, i) => (
                <div key={i} className="h-7 w-7 rounded-full border-2 border-background bg-secondary text-secondary-foreground flex items-center justify-center text-[10px] font-medium">
                  {c}
                </div>
              ))}
            </div>
            <span>Trusted by 2,400+ professionals at FAANG and YC startups</span>
          </motion.div>
        </div>

        <div className="relative h-[500px] w-full">
          <ConnectionLines />
          <FloatingResume />
          <FloatingJobCard delay={1.0} x={320} y={40} company="Linear" role="Senior Product Designer" match={96} accent />
          <FloatingJobCard delay={1.2} x={340} y={210} company="Stripe" role="Staff Engineer" match={92} />
          <FloatingJobCard delay={1.4} x={360} y={310} company="OpenAI" role="AI Product Manager" match={94} accent />

          <motion.div
            initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.7, delay: 1.6, ease: EASE }}
            className="absolute bottom-0 left-2 rounded-2xl bg-foreground text-background px-4 py-3 shadow-elegant flex items-center gap-2"
          >
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full rounded-full bg-accent pulse-ring" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
            </span>
            <span className="text-sm">Discovery agent · 312 roles today</span>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
