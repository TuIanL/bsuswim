import { workflowSteps } from "@/lib/content";
import { Section } from "@/components/ui";

export function SystemFlow() {
  return (
    <Section
      id="system"
      eyebrow="Capture To Intelligence"
      title="移动采集到AI分析"
      description="从岸边小车跟随拍摄，到双摄画面拼接，再到姿态识别和训练复盘，智泳云枢把泳道训练转化为可分析的运动数据。"
    >
      <div className="grid gap-px overflow-hidden border border-white/10 bg-white/10 md:grid-cols-2 lg:grid-cols-4">
        {workflowSteps.map(({ Icon, ...step }) => (
          <article key={step.eyebrow} className="bg-brand-black p-6 sm:p-8">
            <Icon className="mb-10 text-white" size={28} strokeWidth={1.5} />
            <p className="text-[10px] font-bold uppercase tracking-ultra text-brand-muted">{step.eyebrow}</p>
            <h3 className="mt-4 text-xl font-black tracking-widest text-white">{step.title}</h3>
            <p className="mt-4 text-sm leading-7 text-brand-light">{step.description}</p>
          </article>
        ))}
      </div>
    </Section>
  );
}
