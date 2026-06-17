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
  const { submit } = useAuthSubmit();
  return (
    <AuthLayout
      title="Meet your career agents."
      subtitle="Free forever for your first 50 applications."
      switchLink={<>Already with us? <Link to="/auth/login" className="text-foreground underline-offset-4 hover:underline">Sign in</Link></>}
    >
      <form onSubmit={submit} className="mt-6 space-y-4">
        <AuthInput label="Full name" required autoComplete="name" placeholder="Alex Morgan" />
        <AuthInput label="Email" type="email" autoComplete="email" required placeholder="you@company.com" />
        <AuthInput label="Password" type="password" autoComplete="new-password" required placeholder="At least 8 characters" />
        <AuthSubmit label="Create account" />
        <p className="text-[11px] text-muted-foreground">By continuing you agree to our Terms and Privacy.</p>
      </form>
    </AuthLayout>
  );
}
