"use client";
import { createFileRoute } from "@tanstack/react-router";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { PageHeader } from "@/components/shell/sidebar";
import { api } from "@/lib/api";
import type { Application, ApplicationStage } from "@/lib/types";

export const Route = createFileRoute("/app/applications")({
  head: () => ({
    meta: [
      { title: "Applications — Aria" },
      { name: "description", content: "Track every application across every stage." },
    ],
  }),
  component: ApplicationsPage,
});

const STAGES: { id: ApplicationStage; label: string }[] = [
  { id: "matching", label: "Matching" },
  { id: "applying", label: "Applying" },
  { id: "applied", label: "Applied" },
  { id: "assessment", label: "Assessment" },
  { id: "interview", label: "Interview" },
  { id: "offer", label: "Offer" },
  { id: "rejected", label: "Rejected" },
];

function Card({ app }: { app: Application }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: app.id });
  return (
    <div
      ref={setNodeRef}
      {...attributes}
      {...listeners}
      style={{ opacity: isDragging ? 0.3 : 1 }}
      className="rounded-xl border border-border bg-card p-3 shadow-soft hover:shadow-elegant transition-shadow cursor-grab active:cursor-grabbing select-none"
    >
      <div className="flex items-start gap-2.5">
        <div className="h-8 w-8 rounded-lg bg-foreground text-background flex items-center justify-center font-display text-sm flex-shrink-0">
          {app.companyLogo}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs text-muted-foreground truncate">{app.company}</div>
          <div className="text-sm font-medium leading-tight truncate">{app.title}</div>
        </div>
      </div>
      <div className="mt-3 flex items-center justify-between text-[11px] text-muted-foreground">
        <span>{app.location || "Remote"}</span>
        <span>{app.updatedAt}</span>
      </div>
    </div>
  );
}

function Column({ stage, items }: { stage: typeof STAGES[number]; items: Application[] }) {
  const { setNodeRef, isOver } = useDroppable({ id: stage.id });
  return (
    <div className="flex flex-col min-w-[260px] w-[260px] flex-shrink-0 select-none">
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="flex items-center gap-2">
          <span className="font-display text-sm">{stage.label}</span>
          <span className="text-xs text-muted-foreground tabular-nums">{items.length}</span>
        </div>
      </div>
      <div
        ref={setNodeRef}
        className={`flex-1 rounded-2xl border border-dashed p-2 space-y-2 min-h-[400px] transition-colors ${
          isOver ? "border-accent bg-accent/5" : "border-border bg-muted/30"
        }`}
      >
        {items.map((a) => (
          <motion.div key={a.id} layout transition={{ duration: 0.2 }}>
            <Card app={a} />
          </motion.div>
        ))}
        {items.length === 0 && (
          <div className="text-center text-[11px] text-muted-foreground py-8">No items</div>
        )}
      </div>
    </div>
  );
}

function ApplicationsPage() {
  const [apps, setApps] = useState<Application[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));

  const loadApps = async () => {
    try {
      const res = await api.getApplications();
      const mapped = (res.applications || []).map((app: any) => ({
        id: app.id,
        jobId: app.job_id || app.id,
        title: app.title,
        company: app.company,
        companyLogo: app.company_logo || app.company?.[0]?.toUpperCase() || "?",
        stage: app.stage as ApplicationStage,
        updatedAt: app.updated_at ? new Date(app.updated_at).toLocaleDateString() : "",
        salary: app.salary || "",
        location: app.location || "",
      }));
      setApps(mapped);
    } catch (err) {
      console.error("Failed to load applications:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApps();

    const handleAppCompleted = (e: Event) => {
      console.log("🔄 [Applications Board] Received application_completed event. Re-fetching board data...", (e as CustomEvent).detail);
      loadApps();
    };

    window.addEventListener("aria:application_completed", handleAppCompleted);
    return () => {
      window.removeEventListener("aria:application_completed", handleAppCompleted);
    };
  }, []);

  const onEnd = async (e: DragEndEvent) => {
    setActiveId(null);
    const overId = e.over?.id;
    if (!overId) return;

    const targetApp = apps.find((a) => a.id === e.active.id);
    if (!targetApp) return;

    const newStage = overId as ApplicationStage;
    if (targetApp.stage === newStage) return;

    // 1. Optimistic Update
    setApps((prev) =>
      prev.map((a) => (a.id === e.active.id ? { ...a, stage: newStage, updatedAt: new Date().toLocaleDateString() } : a))
    );

    // 2. Persist to Backend
    try {
      await api.createApplication({
        job_id: targetApp.jobId || targetApp.id,
        title: targetApp.title,
        company: targetApp.company,
        company_logo: targetApp.companyLogo,
        stage: newStage,
        location: targetApp.location,
        salary: targetApp.salary,
      });
    } catch (err) {
      console.error("Failed to update application stage on backend:", err);
      // Revert on failure
      setApps((prev) =>
        prev.map((a) => (a.id === e.active.id ? { ...a, stage: targetApp.stage } : a))
      );
    }
  };

  const active = apps.find((a) => a.id === activeId);

  return (
    <>
      <PageHeader title="Applications" subtitle="Drag cards across columns to update stage." />
      
      {loading ? (
        <div className="flex items-center justify-center py-20 text-muted-foreground text-sm">
          Loading applications tracker...
        </div>
      ) : (
        <DndContext sensors={sensors} onDragStart={(e) => setActiveId(String(e.active.id))} onDragEnd={onEnd} onDragCancel={() => setActiveId(null)}>
          <div className="flex gap-4 overflow-x-auto pb-4 -mx-2 px-2 select-none">
            {STAGES.map((s) => (
              <Column key={s.id} stage={s} items={apps.filter((a) => s.id === "matching" ? (a.stage === "matching" || a.stage === "saved") : a.stage === s.id)} />
            ))}
          </div>
          <DragOverlay>
            {active && (
              <div className="rotate-2">
                <Card app={active} />
              </div>
            )}
          </DragOverlay>
        </DndContext>
      )}
    </>
  );
}
