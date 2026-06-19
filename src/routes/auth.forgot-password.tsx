import { createFileRoute, Link } from "@tanstack/react-router";
import { AuthInput, AuthLayout, AuthSubmit, useAuthSubmit } from "@/components/auth/auth-layout";

export const Route = createFileRoute("/auth/forgot-password")({
  head: () => ({
    meta: [
      { title: "Reset your password — Aria" },
      { name: "description", content: "Reset the password to your Aria account." },
    ],
  }),
  component: ForgotPage,
});

function ForgotPage() {
  const { submit } = useAuthSubmit();
  return (
    <AuthLayout
      title="Reset your password."
      subtitle="We'll email you a magic link to get back in."
      showSocial={false}
      switchLink={<>Remembered it? <Link to="/auth/login" className="text-foreground underline-offset-4 hover:underline">Sign in</Link></>}
    >
      <form onSubmit={submit} className="mt-6 space-y-4">
        <AuthInput label="Email" type="email" autoComplete="email" required placeholder="you@company.com" />
        <AuthSubmit label="Send reset link" />
      </form>
    </AuthLayout>
  );
}
