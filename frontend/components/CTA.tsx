import { AnchorButton, Section } from "@/components/ui";

export function CTA() {
  return (
    <Section id="contact" className="bg-[#080808]">
      <div className="mx-auto max-w-4xl text-center">
        <p className="text-xs font-black uppercase tracking-ultra text-brand-light">Ready For Field Testing</p>
        <h2 className="mt-5 text-4xl font-black uppercase tracking-widest text-white sm:text-6xl">
          让泳姿分析进入连续侧面视角
        </h2>
        <p className="mx-auto mt-6 max-w-2xl text-sm leading-7 text-brand-light sm:text-base">
          面向校队、俱乐部与体育科研场景，智泳云枢将采集、拼接与姿态识别连接成完整训练复盘链路。
        </p>
        <div className="mt-9">
          <AnchorButton href="/platform" className="min-h-14 px-9">
            Start Analysis
          </AnchorButton>
        </div>
        <p className="mt-5 text-[10px] font-bold uppercase tracking-ultra text-brand-muted">
          Field Deployment · Coach Review · Research Ready
        </p>
      </div>
    </Section>
  );
}
