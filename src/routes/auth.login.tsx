import { createFileRoute, Link } from "@tanstack/react-router";
import { AuthInput, AuthLayout, AuthSubmit, useAuthSubmit } from "@/components/auth/auth-layout";

export const Route = createFileRoute("/auth/login")({
  head: () => ({
    meta: [
      { title: "Sign in — Aria" },
      { name: "description", content: "Sign in to your Aria account and continue your AI-powered job search." },
    ],
  }),
  component: LoginPage,
});

function LoginPage() {
  const { submit } = useAuthSubmit();
  return (
    <AuthLayout
      title="Welcome back."
      subtitle="Sign in to pick up where your agents left off."
      switchLink={<>New to Aria? <Link to="/auth/register" className="text-foreground underline-offset-4 hover:underline">Create an account</Link></>}
    >
      <form onSubmit={submit} className="mt-6 space-y-4">
        <AuthInput label="Email" type="email" autoComplete="email" required placeholder="you@company.com" />
        <AuthInput label="Password" type="password" autoComplete="current-password" required placeholder="••••••••" />
        <div className="flex justify-end">
          <Link to="/auth/forgot-password" className="text-xs text-muted-foreground hover:text-foreground">Forgot password?</Link>
        </div>
        <AuthSubmit label="Sign in" />
      </form>
    </AuthLayout>
  );
}
