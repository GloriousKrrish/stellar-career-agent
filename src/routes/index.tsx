import { createFileRoute } from "@tanstack/react-router";
import { MarketingNav } from "@/components/landing/marketing-nav";
import { Hero } from "@/components/landing/hero";
import { TrustSection } from "@/components/landing/trust";
import { Workflow } from "@/components/landing/workflow";
import { FeatureSplits } from "@/components/landing/features";
import { CTA, Footer } from "@/components/landing/cta-footer";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Aria — Your AI Career Agent" },
      { name: "description", content: "Upload your resume once. Let intelligent agents discover, evaluate and apply to the most relevant jobs across the web." },
      { property: "og:title", content: "Aria — Your AI Career Agent" },
      { property: "og:description", content: "Six AI agents that find, match and apply to jobs while you focus on your future." },
    ],
  }),
  component: Index,
});

function Index() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <MarketingNav />
      <main>
        <Hero />
        <TrustSection />
        <Workflow />
        <FeatureSplits />
        <CTA />
      </main>
      <Footer />
    </div>
  );
}
