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
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";
import { PageHeader } from "@/components/shell/sidebar";
import { listApplications, createOrUpdateApplication } from "@/lib/api";

export const Route = createFileRoute("/app/applications")({
  head: () => ({
    meta: [
      { title: "Applications — Aria" },
      { name: "description", content: "Track every application across every stage." },
    ],
  }),
  component: ApplicationsPage,
});

type ApplicationStage = "Saved" | "Applied" | "Assessment" | "Interview" | "Offer" | "Rejected";

const STAGES: { id: ApplicationStage; label: string }[] = [
  { id: "Saved", label: "Saved" },
  { id: "Applied", label: "Applied" },
  { id: "Assessment", label: "Assessment" },
  { id: "Interview", label: "Interview" },
  { id: "Offer", label: "Offer" },
  { id: "Rejected", label: "Rejected" },
];

function Card({ app }: { app: any }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: app.id });
  return (
    <div
      ref={setNodeRef}
      {...attributes}
      {...listeners}
      style={{ opacity: isDragging ? 0 : 1 }}
      className="rounded-xl border border-border bg-card p-3 shadow-soft hover:shadow-elegant transition-shadow cursor-grab active:cursor-grabbing"
    >
      <div className="flex items-start gap-2.5">
        <div className="h-8 w-8 rounded-lg bg-foreground text-background flex items-center justify-center font-display text-sm flex-shrink-0">
          {app.company_logo || app.company?.[0]?.toUpperCase() || "?"}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs text-muted-foreground truncate">{app.company}</div>
          <div className="text-sm font-medium leading-tight truncate">{app.title}</div>
        </div>
      </div>
      <div className="mt-3 flex items-center justify-between text-[11px] text-muted-foreground">
        <span>{app.location || "Remote"}</span>
        <span>{app.updated_at ? new Date(app.updated_at).toLocaleDateString() : "Recently"}</span>
      </div>
    </div>
  );
}

function Column({ stage, items }: { stage: typeof STAGES[number]; items: any[] }) {
  const { setNodeRef, isOver } = useDroppable({ id: stage.id });
  return (
    <div className="flex flex-col min-w-[260px] w-[260px] flex-shrink-0">
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
          <motion.div key={a.id} layout transition={{ duration: 0.3 }}>
            <Card app={a} />
          </motion.div>
        ))}
        {items.length === 0 && (
          <div className="text-center text-[11px] text-muted-foreground py-8">No cards in this stage</div>
        )}
      </div>
    </div>
  );
}

function ApplicationsPage() {
  const [apps, setApps] = useState<any[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));

  useEffect(() => {
    async function loadApps() {
      try {
        const res = await listApplications();
        setApps(res.applications || []);
      } catch (err: any) {
        setError(err.message || "Failed to load applications");
      } finally {
        setLoading(false);
      }
    }
    loadApps();
  }, []);

  const onEnd = async (e: DragEndEvent) => {
    setActiveId(null);
    const overId = e.over?.id as ApplicationStage | undefined;
    if (!overId) return;

    const targetApp = apps.find((a) => a.id === e.active.id);
    if (!targetApp) return;

    // Optimistically update stage
    setApps((prev) =>
      prev.map((a) => (a.id === e.active.id ? { ...a, stage: overId } : a))
    );

    try {
      await createOrUpdateApplication({
        job_id: targetApp.job_id,
        title: targetApp.title,
        company: targetApp.company,
        company_logo: targetApp.company_logo,
        stage: overId,
        location: targetApp.location,
        salary: targetApp.salary,
        url: targetApp.url,
      });
    } catch (err: any) {
      setError("Failed to sync status with server");
      // Revert stage on failure
      setApps((prev) =>
        prev.map((a) => (a.id === e.active.id ? { ...a, stage: targetApp.stage } : a))
      );
    }
  };

  const active = apps.find((a) => a.id === activeId);

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-accent" />
          <span className="text-sm text-muted-foreground">Loading applications board...</span>
        </div>
      </div>
    );
  }

  return (
    <>
      <PageHeader title="Applications" subtitle="Drag cards across columns to update stage." />
      
      {error && (
        <div className="mb-4 text-xs text-red-500 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/30 rounded-xl p-3">
          {error}
        </div>
      )}

      {apps.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-border bg-card p-16 text-center text-muted-foreground shadow-soft">
          <div className="font-display text-lg text-foreground">No applications found</div>
          <p className="text-sm mt-1 max-w-md mx-auto">
            You haven't saved or applied to any jobs yet. Open a matched job and click "Apply via Aria" or "View Match Details" to save it here.
          </p>
        </div>
      ) : (
        <DndContext sensors={sensors} onDragStart={(e) => setActiveId(String(e.active.id))} onDragEnd={onEnd} onDragCancel={() => setActiveId(null)}>
          <div className="flex gap-4 overflow-x-auto pb-4 -mx-2 px-2">
            {STAGES.map((s) => (
              <Column key={s.id} stage={s} items={apps.filter((a) => a.stage === s.id)} />
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
