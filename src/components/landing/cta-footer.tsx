import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { Logo } from "../brand/logo";

export function CTA() {
  return (
    <section className="px-6 py-28">
      <div className="mx-auto max-w-5xl rounded-[2.5rem] bg-foreground text-background p-12 md:p-16 relative overflow-hidden">
        <div className="absolute -top-32 -right-32 h-72 w-72 rounded-full opacity-30 blur-3xl"
             style={{ background: "radial-gradient(circle, oklch(0.62 0.07 55), transparent 70%)" }} />
        <div className="relative">
          <h2 className="font-display text-4xl md:text-6xl tracking-tight max-w-3xl text-balance">
            Hand the search to Aria. Keep your evenings.
          </h2>
          <p className="mt-5 max-w-xl text-background/70 text-lg">
            Try Aria free. No credit card, no spam, no recruiter calls — until you ask for them.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/auth/register" className="group inline-flex items-center gap-2 rounded-full bg-background text-foreground px-6 py-3 text-sm font-medium hover:opacity-90 transition">
              Start free
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
            <Link to="/auth/login" className="inline-flex items-center gap-2 rounded-full border border-background/20 px-6 py-3 text-sm font-medium hover:bg-background/10 transition">
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

export function Footer() {
  return (
    <footer className="px-6 pb-12 pt-8">
      <div className="mx-auto max-w-6xl flex flex-col md:flex-row gap-6 justify-between items-start md:items-center border-t border-border pt-8">
        <div className="flex items-center gap-4">
          <Logo />
          <span className="text-xs text-muted-foreground">© {new Date().getFullYear()} Aria Labs, Inc.</span>
        </div>
        <div className="flex gap-6 text-xs text-muted-foreground">
          <a href="#" className="hover:text-foreground">Privacy</a>
          <a href="#" className="hover:text-foreground">Terms</a>
          <a href="#" className="hover:text-foreground">Security</a>
          <a href="#" className="hover:text-foreground">Press</a>
        </div>
      </div>
    </footer>
  );
}
