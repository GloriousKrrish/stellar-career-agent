"use client";
import { Link, useNavigate } from "@tanstack/react-router";
import { type FormEvent, type ReactNode, useState } from "react";
import { motion } from "framer-motion";
import { Logo } from "@/components/brand/logo";
import { signIn } from "@/lib/auth";

function SocialButton({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <button
      type="button"
      className="flex-1 inline-flex items-center justify-center gap-2 rounded-xl border border-border bg-card px-4 py-2.5 text-sm hover:bg-muted transition-colors"
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

export function AuthLayout({
  title,
  subtitle,
  switchLink,
  children,
  showSocial = true,
}: {
  title: string;
  subtitle: string;
  switchLink: ReactNode;
  children: ReactNode;
  showSocial?: boolean;
}) {
  return (
    <div className="min-h-screen flex grain">
      {/* Form side */}
      <div className="flex-1 flex flex-col px-6 py-10 md:px-16">
        <Logo />
        <div className="flex-1 flex items-center justify-center">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            className="w-full max-w-sm"
          >
            <h1 className="font-display text-3xl tracking-tight">{title}</h1>
            <p className="mt-2 text-sm text-muted-foreground">{subtitle}</p>

            {showSocial && (
              <>
                <div className="mt-7 flex gap-2">
                  <SocialButton label="Google" icon={<svg viewBox="0 0 24 24" className="h-4 w-4"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.07 5.07 0 0 1-2.2 3.33v2.77h3.57c2.08-1.92 3.27-4.74 3.27-8.11z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.99.67-2.26 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23z"/><path fill="#FBBC05" d="M5.84 14.1A6.6 6.6 0 0 1 5.5 12c0-.73.13-1.44.34-2.1V7.06H2.18A11 11 0 0 0 1 12c0 1.78.43 3.46 1.18 4.94l3.66-2.84z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.07.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1A11 11 0 0 0 2.18 7.06l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38z"/></svg>} />
                  <SocialButton label="LinkedIn" icon={<svg viewBox="0 0 24 24" className="h-4 w-4" fill="#0A66C2"><path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2zM8 17V10H5.5v7H8zm-1.25-8.2a1.45 1.45 0 1 0 0-2.9 1.45 1.45 0 0 0 0 2.9zM18.5 17v-3.9c0-2.1-1.1-3.1-2.6-3.1-1.2 0-1.8.7-2.1 1.2V10h-2.5v7h2.5v-3.7c0-.7.1-1.5 1.1-1.5s1.1.9 1.1 1.5V17h2.5z"/></svg>} />
                  <SocialButton label="GitHub" icon={<svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor"><path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.9.58.1.79-.25.79-.55v-2c-3.2.7-3.87-1.36-3.87-1.36-.52-1.32-1.27-1.67-1.27-1.67-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.02 1.76 2.69 1.25 3.35.96.1-.74.4-1.25.72-1.54-2.55-.3-5.23-1.28-5.23-5.7 0-1.26.45-2.29 1.18-3.1-.12-.3-.51-1.47.11-3.06 0 0 .96-.31 3.15 1.18a10.9 10.9 0 0 1 5.74 0c2.18-1.49 3.14-1.18 3.14-1.18.63 1.59.23 2.76.11 3.06.74.81 1.18 1.84 1.18 3.1 0 4.43-2.69 5.4-5.25 5.69.42.36.78 1.05.78 2.12v3.14c0 .3.21.66.8.55A11.5 11.5 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5z"/></svg>} />
                </div>
                <div className="mt-6 flex items-center gap-3 text-xs text-muted-foreground">
                  <div className="flex-1 h-px bg-border" />
                  or with email
                  <div className="flex-1 h-px bg-border" />
                </div>
              </>
            )}

            {children}

            <p className="mt-6 text-sm text-muted-foreground">{switchLink}</p>
          </motion.div>
        </div>
        <div className="text-xs text-muted-foreground">© Aria Labs</div>
      </div>

      {/* Visual side */}
      <div className="hidden lg:block flex-1 relative overflow-hidden border-l border-border bg-muted">
        <div className="absolute inset-0">
          <div className="absolute top-1/4 left-1/4 h-96 w-96 rounded-full blur-3xl opacity-40"
               style={{ background: "radial-gradient(circle, oklch(0.7 0.06 55), transparent 70%)" }} />
          <div className="absolute bottom-10 right-10 h-80 w-80 rounded-full blur-3xl opacity-30"
               style={{ background: "radial-gradient(circle, oklch(0.8 0.05 75), transparent 70%)" }} />
        </div>
        <div className="absolute inset-0 flex items-center justify-center p-12">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
            className="max-w-md"
          >
            <blockquote className="font-display text-3xl leading-snug tracking-tight text-balance">
              "Aria found me three roles I never would have seen — and one of them is my new job."
            </blockquote>
            <div className="mt-6 flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-foreground text-background flex items-center justify-center font-display">N</div>
              <div>
                <div className="text-sm font-medium">Naomi Chen</div>
                <div className="text-xs text-muted-foreground">Staff PM, ex-Stripe</div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}

import { api } from "@/lib/api";

export function AuthInput({
  label,
  type = "text",
  placeholder,
  required,
  autoComplete,
  name,
}: {
  label: string;
  type?: string;
  placeholder?: string;
  required?: boolean;
  autoComplete?: string;
  name?: string;
}) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <input
        type={type}
        placeholder={placeholder}
        required={required}
        autoComplete={autoComplete}
        name={name}
        className="mt-1.5 w-full rounded-xl border border-border bg-card px-4 py-2.5 text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 transition"
      />
    </label>
  );
}

export function AuthSubmit({ label, disabled }: { label: string; disabled?: boolean }) {
  return (
    <button
      type="submit"
      disabled={disabled}
      className="w-full rounded-xl bg-foreground text-background px-4 py-2.5 text-sm font-medium hover:opacity-90 disabled:opacity-50 transition"
    >
      {label}
    </button>
  );
}

export function useAuthSubmit(redirectTo: "/app/dashboard" | "/app/onboarding" = "/app/dashboard") {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const formData = new FormData(e.currentTarget);
    const email = formData.get("email") as string;
    const password = formData.get("password") as string;
    const name = formData.get("name") as string;

    try {
      if (redirectTo === "/app/onboarding") {
        await api.register(name || "New User", email, password);
      } else {
        await api.login(email, password);
      }
      navigate({ to: redirectTo });
    } catch (err: any) {
      setError(err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return {
    loading,
    error,
    submit,
  };
}

export { Link };

