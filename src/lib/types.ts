export type Job = {
  id: string;
  title: string;
  company: string;
  companyLogo: string; // single letter
  location: string;
  remote: "Remote" | "Hybrid" | "Onsite";
  salary: string;
  salaryMin: number;
  salaryMax: number;
  experience: "Entry" | "Mid" | "Senior" | "Staff" | "Principal";
  industry: string;
  postedAt: string;
  match: number;
  aiRecommendation: string;
  description: string;
  responsibilities: string[];
  requirements: string[];
  niceToHave: string[];
  benefits: string[];
  skills: string[];
  saved?: boolean;
  url?: string;
  source?: string;
};

export type ApplicationStage =
  | "saved"
  | "applied"
  | "assessment"
  | "interview"
  | "offer"
  | "rejected";

export type Application = {
  id: string;
  jobId: string;
  title: string;
  company: string;
  companyLogo: string;
  stage: ApplicationStage;
  updatedAt: string;
  salary: string;
  location: string;
};

export type AgentStatus = "active" | "idle" | "thinking" | "paused";

export type Agent = {
  id: string;
  name: string;
  role: string;
  description: string;
  status: AgentStatus;
  progress: number;
  tasksToday: number;
  tasksTotal: number;
  recentActions: { time: string; text: string }[];
};

export type ActivityEvent = {
  id: string;
  agent: string;
  text: string;
  time: string;
  kind: "discover" | "match" | "apply" | "interview" | "info";
};

export type Notification = {
  id: string;
  title: string;
  body: string;
  time: string;
  unread: boolean;
};
