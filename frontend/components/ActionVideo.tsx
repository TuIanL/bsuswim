import { Play } from "lucide-react";
import { videoHighlights } from "@/lib/content";
import { MediaFrame, Section } from "@/components/ui";

export function ActionVideo() {
  return (
    <Section
      eyebrow="See It In Action"
      title="动态演示"
      description="预留真实采集视频位置。当前以技术演示框展示双摄拼接与分析流程。"
    >
      <MediaFrame className="aspect-video">
        <div className="relative z-10 flex h-full items-center justify-center p-6">
          <div className="absolute inset-x-8 top-1/2 h-px bg-white/25" />
          <div className="absolute inset-x-12 top-[58%] h-px bg-white/10" />
          <div className="grid size-20 place-items-center border border-white bg-black/70 text-white shadow-white-glow">
            <Play size={28} fill="currentColor" />
          </div>
          <div className="absolute bottom-5 left-5 right-5 flex flex-wrap justify-between gap-3 text-[10px] font-bold uppercase tracking-ultra text-brand-light">
            <span>Above + Underwater Feed</span>
            <span>16:9 Demo Placeholder</span>
          </div>
        </div>
      </MediaFrame>
      <div className="mt-6 grid gap-px border border-white/10 bg-white/10 sm:grid-cols-3">
        {videoHighlights.map(({ Icon, text }) => (
          <div key={text} className="flex items-center gap-3 bg-brand-black p-5">
            <Icon size={18} strokeWidth={1.5} />
            <span className="text-xs font-bold uppercase tracking-widest text-brand-light">{text}</span>
          </div>
        ))}
      </div>
    </Section>
  );
}
