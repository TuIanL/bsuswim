import { testimonials } from "@/lib/content";
import { Section } from "@/components/ui";

export function Testimonials() {
  return (
    <Section
      eyebrow="Trusted By Training Teams"
      title="教练与团队视角"
      description="首版用训练场景化背书表达系统价值，后续可替换为真实用户评价。"
    >
      <div className="grid gap-5 lg:grid-cols-3">
        {testimonials.map((item, index) => (
          <article key={item.name} className="border border-white/15 bg-[#111111] p-6">
            <p className="min-h-32 text-lg leading-8 text-white">“{item.quote}”</p>
            <div className="mt-8 flex items-center gap-4 border-t border-white/10 pt-5">
              <div className="grid size-11 place-items-center rounded-full border border-white/20 bg-black text-xs font-black">
                {String(index + 1).padStart(2, "0")}
              </div>
              <div>
                <p className="text-xs font-black uppercase tracking-widest text-white">{item.name}</p>
                <p className="mt-1 text-xs text-brand-muted">{item.role}</p>
              </div>
            </div>
          </article>
        ))}
      </div>
    </Section>
  );
}
