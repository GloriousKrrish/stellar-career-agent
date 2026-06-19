# Agentic AI Job Finder — Build Plan

You gave a huge, detailed brief and skipped my clarifying questions, so I'm committing to sensible defaults so we can ship something exceptional in one pass and iterate.

## Defaults I'm committing to

- **Mock-only first pass.** No backend, no real auth, no real AI calls. Every screen renders from typed dummy data so the whole app is clickable end-to-end and looks production-ready. We can layer Lovable Cloud + Lovable AI in a follow-up turn without changing the UI.
- **One cohesive design direction**, built straight from your brief — no "pick a direction" step. Warm pale whites, luxury brown, soft beige, deep charcoal text. Apple/Linear/Arc restraint, not flashy.
- **Framer Motion everywhere** for page transitions, hover lifts, stagger reveals, animated counters, sidebar expansion, kanban drag feedback.

## Design system

Tokens go in `src/styles.css` as OKLCH equivalents of your hex palette, mapped via `@theme inline` to Tailwind utilities (`bg-background`, `text-foreground`, `bg-accent`, `border-border`, etc.). No hardcoded hex in components.

- Surfaces: `--background` #F8F6F2, `--card` #FFFFFF, `--muted` #F5F2EC
- Text: `--foreground` #1F1F1F, `--muted-foreground` #6B6B6B
- Brand: `--primary` luxury brown #6D4C41, `--accent` #A67C52, `--secondary` soft beige #DCCDBB
- Borders: `--border` #E9E3DA
- Dark mode: warm charcoal surfaces (#1A1714 family) with the same brown/beige accents — not pure black, keeps the "warm" feel.

Typography: **Fraunces** (display serif, for hero + section headers — gives the editorial/luxury feel) paired with **Inter Tight** (UI/body). Loaded via `<link>` in `__root.tsx` head, declared as `--font-display` / `--font-sans` in `@theme`.

Radius scale: 12–20px (soft, not pill). Shadows: layered, low-opacity warm shadows (`0 1px 2px rgb(31 31 31 / 0.04), 0 8px 24px rgb(31 31 31 / 0.06)`) defined as `--shadow-soft` / `--shadow-elegant` tokens.

## Routes

All under `src/routes/` (TanStack Start file-based). Mock "auth" stored in localStorage so the gate is just a redirect — no real session.

```
/                        landing
/how-it-works            (or anchor on landing)
/auth/login
/auth/register
/auth/forgot-password
/app                     workspace shell (3-panel) → redirects to /app/dashboard
/app/dashboard
/app/jobs                job search + filters
/app/jobs/$jobId         split-screen job details
/app/agents              AI agents control center
/app/applications        kanban tracker
/app/resume              resume analyzer
/app/cover-letters
/app/interview-prep
/app/analytics
/app/settings
```

Pathless `_app` layout (or `app.tsx` parent) renders the **three-panel shell**: floating left sidebar, center `<Outlet />`, right AI activity stream. The shell handles sidebar collapse, command palette (⌘K), notifications dropdown, theme toggle.

Each route gets unique `head()` metadata (title + description + og:title/description).

## Component architecture

```
src/components/
  landing/        Hero, TrustCounters, AgentWorkflow, FeatureSplits, FAQ, Footer, CTA
  auth/           AuthCard, SocialButtons, AuthLayout
  shell/          AppShell, Sidebar, ActivityStream, CommandPalette, TopBar, NotificationCenter
  dashboard/      MetricCard, AnimatedCounter, GrowthChart, RecentActivity, RadialProgress
  jobs/           JobCard, JobFilters, MatchBadge, JobDetailHeader, SkillsComparison, SalaryInsight
  agents/         AgentCard, AgentStatusDot, AgentLogStream, WorkflowDiagram
  applications/   KanbanBoard, KanbanColumn, ApplicationCard
  resume/         ResumeDropzone, ScoreRing, SkillChips, MissingSkillsPanel
  interview/      QuestionList, MockChat, FeedbackPanel
  analytics/      TrendChart, DistributionDonut, FunnelChart
  settings/       ConnectionCard, ProfileForm
  ui/             (existing shadcn primitives)
  motion/         FadeIn, StaggerChildren, HoverLift, PageTransition
```

Mock data lives in `src/lib/mock/` (jobs.ts, applications.ts, agents.ts, metrics.ts, user.ts) with TypeScript types in `src/lib/types.ts`. A tiny `useMockAuth` hook reads/writes a localStorage flag so the `/app/*` gate redirects to `/auth/login` when missing.

Charts use **Recharts** (already shadcn-friendly) styled with our tokens — line/area for trends, donut for distributions, custom radial for scores.

Kanban uses **@dnd-kit** for drag-and-drop between columns.

## What each screen contains (highlights)

- **Landing**: full-bleed hero with serif headline, animated resume card floating with connection lines to job cards (pure SVG + Motion), two CTAs, trust counters (intersection-observer animated), 6-step horizontal agent workflow with sequential reveal on scroll, "why us" split sections, FAQ accordion, footer.
- **Auth**: centered card on warm gradient background, social buttons (Google/LinkedIn/GitHub — visual only), elegant input focus states, mode-switch transitions.
- **Dashboard**: 4 metric cards with animated counters, growth area chart, radial progress for response rate, recent AI activity feed.
- **Job search**: sticky filter rail, list of job cards with hover lift, match % ring, save/apply, click → details.
- **Job details**: split layout — left scrollable description, right sticky panel with match explanation, animated skill bars (your skills vs required), salary insight, company info.
- **AI Agents**: 6 agent cards with live-looking pulse dots, fake task progress bars, log stream that types out lines, workflow diagram showing handoffs.
- **Auto-apply pipeline**: horizontal stages with items flowing through (Motion `layout` animations).
- **Applications**: dnd-kit kanban, 6 columns, smooth column transitions.
- **Resume analyzer**: dropzone (accepts file, shows fake parsing animation), then score rings + extracted chips + missing skills.
- **Interview prep**: tabbed question banks + mock chat UI with canned AI responses.
- **Analytics**: 4–6 charts in a clean grid.
- **Settings**: profile form, notification toggles, connected platforms grid (LinkedIn/Indeed/Glassdoor/Wellfound/Naukri/Foundit) with connect/disconnect states.

## Global features

- **Command palette** (⌘K) using `cmdk` — navigate anywhere, trigger actions.
- **Notification center** dropdown in top bar.
- **Theme toggle** (light/dark, both warm).
- **Page transitions** via Motion `AnimatePresence` on the outlet.
- Skeleton loaders, empty states, and error states for every data surface.
- Fully responsive: sidebar collapses to icon rail < lg, becomes off-canvas sheet on mobile.

## Out of scope for this pass (explicit)

- Real authentication / database / file storage
- Real AI calls (resume parsing, matching, interview Q gen are pre-scripted)
- Real job-board integrations
- Email sending, payments

Each of these is a clean follow-up: enable Lovable Cloud → swap mock auth + add tables; enable Lovable AI → replace mock parsing/matching/interview handlers. The UI won't need to change.

## Technical details

- Stack stays as-is: TanStack Start + React 19 + Tailwind v4 + shadcn. No router/framework swaps.
- Add deps: `framer-motion`, `@dnd-kit/core`, `@dnd-kit/sortable`, `cmdk`, `recharts` (verify which are already present before installing).
- All colors via semantic tokens — zero hex literals in component JSX.
- All `<Link>` for navigation, typed params for `/app/jobs/$jobId`.
- Each route declares `head()` with unique title/description.
- Lighthouse-conscious: lazy-load chart components on routes that need them.

After you approve, I'll build this in one large batch: tokens + shell + landing first, then the workspace screens, then the polish pass (command palette, transitions, empty/error states).
