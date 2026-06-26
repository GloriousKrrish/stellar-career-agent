"use client";
import { createFileRoute } from "@tanstack/react-router";
import { Send, Sparkles } from "lucide-react";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PageHeader } from "@/components/shell/sidebar";

import { getCurrentUser } from "@/lib/auth";

export const Route = createFileRoute("/app/interview-prep")({
  head: () => ({
    meta: [
      { title: "Interview Prep — Aria" },
      { name: "description", content: "Mock interviews and tailored question banks." },
    ],
  }),
  component: InterviewPage,
});

const tabs = ["Technical", "Behavioral", "Mock Interview"] as const;

const QUESTIONS = {
  Technical: [
    "Walk me through how you'd design Stripe's payment retry system.",
    "Why is invalidating a CDN cache for SSR pages tricky?",
    "Implement a debounced React hook from scratch.",
    "How would you architect a multi-tenant Postgres schema?",
    "Explain CRDTs in the context of collaborative editing.",
  ],
  Behavioral: [
    "Tell me about a time you disagreed with your manager.",
    "Describe a project you led that didn't go to plan.",
    "How do you give feedback to a senior engineer?",
    "Walk through a moment you raised the bar on your team.",
    "What's the hardest tradeoff you've made in the last year?",
  ],
  "Mock Interview": [],
};

function MockChat() {
  const user = getCurrentUser();
  const firstName = user?.name ? user.name.split(" ")[0] : "there";
  const [messages, setMessages] = useState<{ role: "ai" | "you"; text: string }[]>([
    { role: "ai", text: `Hey ${firstName}. Let's start with: tell me about a recent project you're proud of.` },
  ]);
  const [input, setInput] = useState("");

  const send = () => {
    if (!input.trim()) return;
    const userText = input;
    setMessages((m) => [...m, { role: "you", text: userText }]);
    setInput("");
    setTimeout(() => {
      setMessages((m) => [...m, { role: "ai", text: "Strong opener. Push deeper on the metrics — what changed for users after you shipped?" }]);
    }, 900);
  };

  return (
    <div className="rounded-2xl border border-border bg-card shadow-soft flex flex-col h-[540px]">
      <div className="px-5 py-3 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-accent" />
          <div className="font-display">Mock with Aria</div>
        </div>
        <div className="text-xs text-muted-foreground">Behavioral · Round 1</div>
      </div>
      <div className="flex-1 overflow-y-auto p-5 space-y-3">
        <AnimatePresence initial={false}>
          {messages.map((m, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${m.role === "you" ? "justify-end" : ""}`}
            >
              <div className={`max-w-[78%] rounded-2xl px-4 py-2.5 text-sm ${m.role === "you" ? "bg-foreground text-background" : "bg-muted"}`}>
                {m.text}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
      <div className="border-t border-border p-3 flex items-center gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Your answer..."
          className="flex-1 rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent"
        />
        <button onClick={send} className="h-9 w-9 inline-flex items-center justify-center rounded-xl bg-foreground text-background hover:opacity-90">
          <Send className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

function InterviewPage() {
  const [tab, setTab] = useState<typeof tabs[number]>("Technical");

  return (
    <>
      <PageHeader title="Interview Preparation" subtitle="Generated for the roles in your pipeline." />

      <div className="flex items-center gap-1 mb-6 border-b border-border">
        {tabs.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`relative px-4 py-2.5 text-sm transition-colors ${tab === t ? "text-foreground" : "text-muted-foreground hover:text-foreground"}`}
          >
            {t}
            {tab === t && <motion.span layoutId="tab" className="absolute bottom-0 inset-x-0 h-0.5 bg-accent" />}
          </button>
        ))}
      </div>

      {tab !== "Mock Interview" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {QUESTIONS[tab].map((q, i) => (
            <motion.div
              key={q}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="rounded-2xl border border-border bg-card p-5 hover:shadow-elegant transition-shadow"
            >
              <div className="flex items-start gap-3">
                <div className="h-7 w-7 rounded-lg bg-muted flex items-center justify-center text-xs font-display flex-shrink-0">
                  {String(i + 1).padStart(2, "0")}
                </div>
                <div className="flex-1">
                  <p className="text-sm leading-relaxed">{q}</p>
                  <div className="mt-3 flex items-center gap-2 text-xs">
                    <button className="rounded-full border border-border px-2.5 py-1 hover:bg-muted">Show outline</button>
                    <button className="inline-flex items-center gap-1 rounded-full bg-foreground text-background px-2.5 py-1">
                      <Sparkles className="h-3 w-3" /> Practice
                    </button>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {tab === "Mock Interview" && <MockChat />}
    </>
  );
}
