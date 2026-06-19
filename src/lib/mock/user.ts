import type { Notification } from "../types";

export const USER = {
  name: "Alex Morgan",
  email: "alex@arialabs.io",
  title: "Senior Product Engineer",
  initials: "AM",
  location: "San Francisco, CA",
  resumeScore: 86,
  atsScore: 92,
  skills: ["TypeScript", "React", "Node", "Design Systems", "Figma", "Postgres", "tRPC", "Motion"],
  missingSkills: ["GraphQL", "Rust", "Kubernetes"],
};

export const NOTIFICATIONS: Notification[] = [
  { id: "n1", title: "Interview scheduled", body: "Linear scheduled a portfolio review for Thursday at 2pm.", time: "10m", unread: true },
  { id: "n2", title: "New 94% match", body: "AI Product Manager at OpenAI matches your resume.", time: "1h", unread: true },
  { id: "n3", title: "Application submitted", body: "Auto Apply Agent submitted your application to Vercel.", time: "3h", unread: false },
  { id: "n4", title: "Stripe moved you forward", body: "Recruiter screen scheduled for next Monday.", time: "Yesterday", unread: false },
];

export const CONNECTIONS = [
  { id: "linkedin", name: "LinkedIn", connected: true, description: "Sync roles, profile and easy apply." },
  { id: "indeed", name: "Indeed", connected: true, description: "Pull millions of roles across industries." },
  { id: "glassdoor", name: "Glassdoor", connected: false, description: "Surface roles with company insights." },
  { id: "wellfound", name: "Wellfound", connected: true, description: "Discover early-stage startup roles." },
  { id: "naukri", name: "Naukri", connected: false, description: "Reach the India market." },
  { id: "foundit", name: "Foundit", connected: false, description: "APAC roles across industries." },
];
