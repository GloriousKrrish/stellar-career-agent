import { createFileRoute, redirect } from "@tanstack/react-router";
import { hasOnboarded } from "@/lib/auth";

export const Route = createFileRoute("/app/")({
  beforeLoad: () => {
    if (typeof window !== "undefined" && !hasOnboarded()) {
      throw redirect({ to: "/app/onboarding" });
    }
    throw redirect({ to: "/app/dashboard" });
  },
});
