import type { Agent, ActivityEvent } from "../types";

/**
 * Empty agent templates — used ONLY as loading-state placeholders before
 * the first real API response arrives.  All metrics start at zero so the
 * UI never shows fake "18,420" or "213" style counts.
 */
export const AGENTS: Agent[] = [
  {
    id: "resume",
    name: "Resume Agent",
    role: "Parses and enhances your resume",
    description: "Extracts skills, experience and signals from your resume in seconds.",
    status: "idle",
    progress: 100,
    tasksToday: 0,
    tasksTotal: 0,
    recentActions: [],
  },
  {
    id: "discovery",
    name: "Discovery Agent",
    role: "Searches the web for jobs",
    description: "Crawls 40+ sources continuously to surface roles before they're saturated.",
    status: "idle",
    progress: 100,
    tasksToday: 0,
    tasksTotal: 0,
    recentActions: [],
  },
  {
    id: "matching",
    name: "Matching Agent",
    role: "Scores fit for every role",
    description: "Compares each role against your resume and preferences using multi-factor scoring.",
    status: "idle",
    progress: 100,
    tasksToday: 0,
    tasksTotal: 0,
    recentActions: [],
  },
  {
    id: "apply",
    name: "AutoApply Agent",
    role: "Autonomous job applications",
    description: "Navigates directly to job listings, fills forms with your profile data, uploads your resume, and submits applications autonomously — or escalates to you when human verification is needed.",
    status: "idle",
    progress: 100,
    tasksToday: 0,
    tasksTotal: 0,
    recentActions: [],
  },
  {
    id: "orchestrator",
    name: "Agent Orchestrator",
    role: "Multi-agent coordination engine",
    description: "Master coordinator that manages the pipeline between Discovery and AutoApply. Polls the database for high-match jobs and dispatches autonomous applications.",
    status: "idle",
    progress: 100,
    tasksToday: 0,
    tasksTotal: 0,
    recentActions: [],
  },
  {
    id: "tracking",
    name: "Tracking Agent",
    role: "Follows up on every application",
    description: "Monitors inbox and platforms to keep your pipeline up to date.",
    status: "idle",
    progress: 100,
    tasksToday: 0,
    tasksTotal: 0,
    recentActions: [],
  },
  {
    id: "interview",
    name: "Interview Agent",
    role: "Coaches you for every round",
    description: "Generates likely questions, runs mock interviews and gives feedback.",
    status: "paused",
    progress: 0,
    tasksToday: 0,
    tasksTotal: 0,
    recentActions: [],
  },
];

/**
 * Empty activity events — no fake feed items.
 * Real events stream via WebSocket.
 */
export const ACTIVITY: ActivityEvent[] = [];
