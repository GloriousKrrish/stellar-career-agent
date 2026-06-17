import { Link } from "@tanstack/react-router";

export function Logo({ className = "" }: { className?: string }) {
  return (
    <Link to="/" className={`inline-flex items-center gap-2 group ${className}`}>
      <span className="relative inline-flex h-8 w-8 items-center justify-center rounded-[10px] bg-primary text-primary-foreground">
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M5 19L12 5l7 14" />
          <path d="M8.5 13.5h7" />
        </svg>
      </span>
      <span className="font-display text-xl tracking-tight">Aria</span>
    </Link>
  );
}
