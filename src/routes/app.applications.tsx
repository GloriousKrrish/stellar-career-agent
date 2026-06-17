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
import { useState } from "react";
import { motion } from "framer-motion";
import { PageHeader } from "@/components/shell/sidebar";
import { APPLICATIONS } from "@/lib/mock/applications";
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
  { id: "saved", label: "Saved" },
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
      style={{ opacity: isDragging ? 0 : 1 }}
      className="rounded-xl border border-border bg-card p-3 shadow-soft hover:shadow-elegant transition-shadow cursor-grab active:cursor-grabbing"
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
        <span>{app.location}</span>
        <span>{app.updatedAt}</span>
      </div>
    </div>
  );
}

function Column({ stage, items }: { stage: typeof STAGES[number]; items: Application[] }) {
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
        className={`flex-1 rounded-2xl border border-dashed p-2 space-y-2 min-h-[200px] transition-colors ${
          isOver ? "border-accent bg-accent/5" : "border-border bg-muted/30"
        }`}
      >
        {items.map((a) => (
          <motion.div key={a.id} layout transition={{ duration: 0.3 }}>
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
  const [apps, setApps] = useState(APPLICATIONS);
  const [activeId, setActiveId] = useState<string | null>(null);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));

  const onEnd = (e: DragEndEvent) => {
    setActiveId(null);
    const overId = e.over?.id;
    if (!overId) return;
    setApps((prev) =>
      prev.map((a) => (a.id === e.active.id ? { ...a, stage: overId as ApplicationStage } : a)),
    );
  };

  const active = apps.find((a) => a.id === activeId);

  return (
    <>
      <PageHeader title="Applications" subtitle="Drag cards across columns to update stage." />
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
    </>
  );
}
