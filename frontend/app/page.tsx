import { AnalysisOutputs } from "@/components/AnalysisOutputs";
import { ActionVideo } from "@/components/ActionVideo";
import { CTA } from "@/components/CTA";
import { FAQ } from "@/components/FAQ";
import { Features } from "@/components/Features";
import { Footer } from "@/components/Footer";
import { Hero } from "@/components/Hero";
import { Navbar } from "@/components/Navbar";
import { Specs } from "@/components/Specs";
import { SystemFlow } from "@/components/SystemFlow";
import { Testimonials } from "@/components/Testimonials";

export default function Home() {
  return (
    <main className="min-h-screen bg-brand-black text-white">
      <Navbar />
      <Hero />
      <SystemFlow />
      <Features />
      <Specs />
      <AnalysisOutputs />
      <Testimonials />
      <ActionVideo />
      <FAQ />
      <CTA />
      <Footer />
    </main>
  );
}
