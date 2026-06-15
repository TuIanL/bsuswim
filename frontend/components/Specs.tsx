import { specs } from "@/lib/content";
import { MediaFrame, Section } from "@/components/ui";

export function Specs() {
  return (
    <Section
      id="specs"
      eyebrow="System Specifications"
      title="系统规格"
      description="规格区块以系统能力为主，便于后续替换真实设备参数。"
    >
      <div className="grid items-center gap-12 lg:grid-cols-[0.92fr_1.08fr]">
        <MediaFrame className="aspect-[4/3]">
          <div className="relative z-10 flex h-full flex-col justify-between p-7">
            <div className="flex justify-between text-[10px] font-bold uppercase tracking-ultra text-brand-muted">
              <span>Pool Lane</span>
              <span>Side Profile</span>
            </div>
            <div className="relative h-60">
              <div className="absolute inset-x-0 top-8 h-px bg-white/20" />
              <div className="absolute inset-x-0 top-20 h-px bg-white/15" />
              <div className="absolute inset-x-0 top-32 h-px bg-white/10" />
              <div className="absolute left-[14%] top-10 h-36 w-1/2 border border-white/25" />
              <div className="absolute left-[22%] top-16 h-6 w-44 border border-white/30" />
              <div className="absolute left-[26%] top-24 h-4 w-36 border border-white/20" />
              <div className="absolute right-[10%] top-3 h-28 w-24 border border-white/35 bg-black/70" />
              <div className="absolute right-[13%] top-44 h-16 w-20 border border-white/25 bg-black/70" />
              <div className="absolute bottom-2 right-[8%] h-10 w-32 border border-white/20" />
            </div>
            <p className="max-w-sm text-sm leading-7 text-brand-light">
              上下摄像头覆盖水面边界两侧，生成完整侧面视频，用于后续姿态识别和训练复盘。
            </p>
          </div>
        </MediaFrame>
        <div className="border-y border-white/10">
          {specs.map(([label, value]) => (
            <div key={label} className="grid gap-2 border-b border-white/10 py-5 last:border-b-0 sm:grid-cols-[0.46fr_0.54fr]">
              <dt className="text-[11px] font-bold uppercase tracking-ultra text-brand-muted">{label}</dt>
              <dd className="text-lg font-semibold tracking-widest text-white">{value}</dd>
            </div>
          ))}
        </div>
      </div>
    </Section>
  );
}
