export const METRICS = {
  jobsDiscovered: 12480,
  applicationsSubmitted: 142,
  interviewsGenerated: 18,
  companiesReached: 89,
  responseRate: 23,
};

export const GROWTH = [
  { day: "Mon", applications: 12, interviews: 1 },
  { day: "Tue", applications: 18, interviews: 2 },
  { day: "Wed", applications: 22, interviews: 3 },
  { day: "Thu", applications: 19, interviews: 2 },
  { day: "Fri", applications: 28, interviews: 4 },
  { day: "Sat", applications: 14, interviews: 3 },
  { day: "Sun", applications: 29, interviews: 3 },
];

export const ROLE_DISTRIBUTION = [
  { name: "Engineering", value: 42 },
  { name: "Design", value: 28 },
  { name: "Product", value: 18 },
  { name: "Growth", value: 12 },
];

export const SALARY_DISTRIBUTION = [
  { band: "$120k", count: 4 },
  { band: "$150k", count: 9 },
  { band: "$180k", count: 18 },
  { band: "$210k", count: 24 },
  { band: "$240k", count: 16 },
  { band: "$280k", count: 8 },
  { band: "$320k+", count: 3 },
];

export const FUNNEL = [
  { stage: "Discovered", value: 12480 },
  { stage: "Matched", value: 612 },
  { stage: "Applied", value: 142 },
  { stage: "Replied", value: 33 },
  { stage: "Interview", value: 18 },
  { stage: "Offer", value: 3 },
];
