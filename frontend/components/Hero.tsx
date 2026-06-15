import { AnchorButton, Eyebrow, MediaFrame } from "@/components/ui";

function ProductSchematic() {
  return (
    <MediaFrame className="aspect-[4/3]">
      <div className="relative z-10 flex h-full flex-col justify-between p-6 sm:p-8">
        <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-ultra text-brand-light">
          <span>Dual Camera Rig</span>
          <span>Live Capture</span>
        </div>
        <div className="relative mx-auto h-52 w-full max-w-lg sm:h-64">
          <div className="absolute left-0 right-0 top-20 h-px bg-white/25" />
          <div className="absolute left-0 right-0 top-32 h-px bg-white/10" />
          <div className="absolute bottom-10 left-8 right-8 h-16 border border-white/25 bg-black/60" />
          <div className="absolute bottom-14 left-16 right-16 h-8 border border-white/10 bg-white/[0.03]" />
          <div className="absolute bottom-4 left-16 size-8 border border-white/35" />
          <div className="absolute bottom-4 right-16 size-8 border border-white/35" />
          <div className="absolute left-1/2 top-3 h-28 w-24 -translate-x-1/2 border border-white/40 bg-black/70 shadow-white-glow" />
          <div className="absolute left-1/2 top-9 h-7 w-16 -translate-x-1/2 border border-white/30" />
          <div className="absolute left-1/2 top-36 h-20 w-24 -translate-x-1/2 border border-white/30 bg-black/70" />
          <div className="absolute left-[14%] top-24 h-px w-[72%] bg-white/40" />
          <div className="absolute left-[18%] top-28 h-px w-[64%] bg-white/20" />
          <div className="absolute bottom-24 left-1/2 h-5 w-40 -translate-x-1/2 border border-white/20" />
        </div>
        <div className="grid grid-cols-3 gap-3 text-[10px] uppercase tracking-widest text-brand-light">
          <span className="border-t border-white/15 pt-3">Above Water</span>
          <span className="border-t border-white/15 pt-3">Side Stitch</span>
          <span className="border-t border-white/15 pt-3">Underwater</span>
        </div>
      </div>
    </MediaFrame>
  );
}

export function Hero() {
  return (
    <section id="top" className="relative min-h-screen overflow-hidden bg-brand-black px-5 pt-28 sm:px-8">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_15%,rgba(255,255,255,0.12),transparent_32%),linear-gradient(180deg,rgba(5,5,5,0),#050505_88%)]" />
      <div className="relative z-10 mx-auto grid min-h-[calc(100vh-7rem)] max-w-7xl items-center gap-14 py-12 lg:grid-cols-[1.05fr_0.95fr]">
        <div>
          <Eyebrow>AI-Powered Swim Motion Analysis</Eyebrow>
          <h1 className="mt-5 max-w-5xl text-5xl font-black uppercase leading-[0.95] tracking-widest text-white sm:text-7xl lg:text-8xl">
            See Every Stroke
          </h1>
          <p className="mt-6 text-xl font-semibold tracking-widest text-white sm:text-2xl">
            智泳云枢
          </p>
          <p className="mt-6 max-w-2xl text-base leading-8 text-brand-light sm:text-lg">
            移动式双摄采集，重建完整侧面泳姿；AI姿态识别，让训练分析有据可依。
            岸边小车沿泳道跟随拍摄，水上与水下画面同步拼接后传输到运算设备完成动作分析。
          </p>
          <div className="mt-9 flex flex-col gap-3 sm:flex-row">
            <AnchorButton href="/platform">进入分析平台</AnchorButton>
            <AnchorButton href="#analysis" variant="outline">
              了解姿态分析
            </AnchorButton>
          </div>
        </div>
        <ProductSchematic />
      </div>
      <a
        href="#system"
        aria-label="向下滚动"
        className="absolute bottom-8 left-1/2 z-20 hidden h-12 w-px -translate-x-1/2 overflow-hidden bg-white/20 sm:block"
      >
        <span className="block h-5 w-px animate-[scrollCue_1.4s_ease-in-out_infinite] bg-white" />
      </a>
    </section>
  );
}
