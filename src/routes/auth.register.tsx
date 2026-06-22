import { createFileRoute, Link } from "@tanstack/react-router";
import { AuthInput, AuthLayout, AuthSubmit, useAuthSubmit } from "@/components/auth/auth-layout";

export const Route = createFileRoute("/auth/register")({
  head: () => ({
    meta: [
      { title: "Create your account — Aria" },
      { name: "description", content: "Create a free Aria account and meet your six AI career agents." },
    ],
  }),
  component: RegisterPage,
});

function RegisterPage() {
  const { submit, loading, error } = useAuthSubmit("/app/onboarding");
  return (
    <AuthLayout
      title="Meet your career agents."
      subtitle="Free forever for your first 50 applications."
      switchLink={<>Already with us? <Link to="/auth/login" className="text-foreground underline-offset-4 hover:underline">Sign in</Link></>}
    >
      <form onSubmit={submit} className="mt-6 space-y-4">
        {error && <div className="text-xs text-red-500 bg-red-50 p-3 rounded-xl border border-red-200">{error}</div>}
        <AuthInput label="Full name" name="name" required autoComplete="name" placeholder="Alex Morgan" />
        <AuthInput label="Email" name="email" type="email" autoComplete="email" required placeholder="you@company.com" />
        <AuthInput label="Password" name="password" type="password" autoComplete="new-password" required placeholder="At least 8 characters" />
        <AuthSubmit label={loading ? "Creating account..." : "Create account"} disabled={loading} />
        <p className="text-[11px] text-muted-foreground">By continuing you agree to our Terms and Privacy.</p>
      </form>
    </AuthLayout>
  );
}

