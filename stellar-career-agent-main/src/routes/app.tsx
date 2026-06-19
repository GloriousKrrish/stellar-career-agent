"use client";
import { createFileRoute, Outlet, redirect, useRouterState } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Sidebar, PageTransition } from "@/components/shell/sidebar";
import { TopBar } from "@/components/shell/top-bar";
import { ActivityStream } from "@/components/shell/activity-stream";
import { CommandPalette } from "@/components/shell/command-palette";
import { isAuthed } from "@/lib/auth";

export const Route = createFileRoute("/app")({
  beforeLoad: () => {
    // SSR-safe: only enforce in browser, but loader runs both. Use typeof window check.
    if (typeof window !== "undefined" && !isAuthed()) {
      throw redirect({ to: "/auth/login" });
    }
  },
  component: AppShell,
});

function AppShell() {
  const [collapsed, setCollapsed] = useState(false);
  const [cmdOpen, setCmdOpen] = useState(false);
  const [activityOpen, setActivityOpen] = useState(true);
  const path = useRouterState({ select: (s) => s.location.pathname });

  // SSR fallback: redirect with effect too
  useEffect(() => {
    if (!isAuthed()) window.location.href = "/auth/login";
  }, []);

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} onCommand={() => setCmdOpen(true)} />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar
          onCommand={() => setCmdOpen(true)}
          onMenu={() => setCollapsed(!collapsed)}
          onToggleActivity={() => setActivityOpen(!activityOpen)}
          activityOpen={activityOpen}
        />
        <main className="flex-1 overflow-y-auto">
          <div className="px-6 lg:px-10 py-8 max-w-[1400px] mx-auto">
            <PageTransition k={path}>
              <Outlet />
            </PageTransition>
          </div>
        </main>
      </div>
      <ActivityStream open={activityOpen} />
      <CommandPalette open={cmdOpen} setOpen={setCmdOpen} />
    </div>
  );
}
