import { analysisOutputs } from "@/lib/content";
import { AnchorButton, Section } from "@/components/ui";

export function AnalysisOutputs() {
  return (
    <Section
      id="analysis"
      eyebrow="Analysis Output"
      title="训练分析输出"
      description="智泳云枢把视频、关键点和节奏信息组织为教练可复盘的技术材料。"
    >
      <div className="grid gap-px border border-white/10 bg-white/10 sm:grid-cols-2 lg:grid-cols-3">
        {analysisOutputs.map(({ Icon, label, title, description }) => (
          <article key={label} className="bg-brand-black p-6 transition hover:bg-brand-dark">
            <Icon className="mb-8 text-white" size={26} strokeWidth={1.4} />
            <p className="text-[10px] font-bold uppercase tracking-ultra text-brand-muted">{label}</p>
            <h3 className="mt-3 text-lg font-black tracking-widest text-white">{title}</h3>
            <p className="mt-4 text-sm leading-7 text-brand-light">{description}</p>
          </article>
        ))}
      </div>
      <div className="mt-10 text-center">
        <AnchorButton href="/platform" variant="outline">
          打开视频分析工作流
        </AnchorButton>
      </div>
    </Section>
  );
}
