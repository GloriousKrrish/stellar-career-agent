import { Link } from "@tanstack/react-router";
import { Logo } from "../brand/logo";

const links = [
  { to: "/", label: "Home" },
  { to: "/#workflow", label: "How it works", anchor: true },
  { to: "/#trust", label: "Numbers", anchor: true },
  { to: "/auth/login", label: "Sign in" },
];

export function MarketingNav() {
  return (
    <header className="fixed top-0 inset-x-0 z-40">
      <div className="mx-auto mt-4 flex max-w-6xl items-center justify-between rounded-full border border-border/60 bg-background/70 px-4 py-2 backdrop-blur-xl shadow-soft">
        <Logo />
        <nav className="hidden md:flex items-center gap-8 text-sm text-muted-foreground">
          {links.slice(1, 3).map((l) =>
            l.anchor ? (
              <a key={l.label} href={l.to} className="hover:text-foreground transition-colors">{l.label}</a>
            ) : (
              <Link key={l.label} to={l.to} className="hover:text-foreground transition-colors">{l.label}</Link>
            ),
          )}
        </nav>
        <div className="flex items-center gap-2">
          <Link to="/auth/login" className="hidden sm:inline-flex text-sm text-muted-foreground hover:text-foreground px-3 py-1.5">Sign in</Link>
          <Link
            to="/auth/register"
            className="inline-flex items-center gap-1.5 rounded-full bg-foreground text-background text-sm font-medium px-4 py-2 hover:opacity-90 transition-opacity"
          >
            Start free
          </Link>
        </div>
      </div>
    </header>
  );
}
