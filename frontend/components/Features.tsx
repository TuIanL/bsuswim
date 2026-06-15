import { features } from "@/lib/content";
import { Section } from "@/components/ui";

export function Features() {
  return (
    <Section
      id="features"
      eyebrow="Built For Performance"
      title="核心能力"
      description="围绕真实泳道训练设计，重点解决连续侧面视角、双层水面信息和动作结构量化的问题。"
    >
      <div className="grid gap-8 md:grid-cols-3">
        {features.map(({ Icon, title, description }) => (
          <article key={title} className="group border-l border-white/15 pl-6">
            <Icon
              className="mb-10 text-white transition group-hover:drop-shadow-[0_0_16px_rgba(255,255,255,0.7)]"
              size={34}
              strokeWidth={1.4}
            />
            <h3 className="text-lg font-black uppercase tracking-widest text-white">{title}</h3>
            <p className="mt-5 text-sm leading-7 text-brand-light">{description}</p>
          </article>
        ))}
      </div>
    </Section>
  );
}
