"use client";

import { Activity, Eye, RadioTower, ScanLine, Timer, Waves } from "lucide-react";
import { captureModeLabels, strokeLabels } from "@/lib/swim-demo-data";
import type { SwimAnalysisJob, SwimAnalysisReport, SwimMetricTone } from "@/lib/swim-types";

const toneStyles: Record<SwimMetricTone, string> = {
  strong: "border-white/50 bg-white text-black",
  watch: "border-white/20 bg-white/12 text-white",
  risk: "border-white/25 bg-black text-white",
  neutral: "border-white/15 bg-white/[0.06] text-brand-light"
};

export function SwimVisualWorkspace({
  job,
  report,
  onOpenReport,
  onOpenTraining,
  onOpenTasks
}: {
  job?: SwimAnalysisJob | null;
  report: SwimAnalysisReport;
  onOpenReport: () => void;
  onOpenTraining: () => void;
  onOpenTasks: () => void;
}) {
  const session = job?.metadata ?? report.session;

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="border border-white/10 bg-[#080808]">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-4 py-3">
          <div>
            <p className="text-[10px] font-black uppercase tracking-ultra text-brand-muted">Side View Workspace</p>
            <h2 className="mt-1 text-lg font-black tracking-widest text-white">{session.sessionTitle}</h2>
          </div>
          <span className="border border-white/15 px-3 py-1 text-[10px] font-black uppercase tracking-widest text-brand-light">
            {report.source === "demo" ? "Demo Layers" : "Local Result"}
          </span>
        </div>

        <div className="relative aspect-video overflow-hidden bg-black">
          <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(255,255,255,0.055)_1px,transparent_1px),linear-gradient(rgba(255,255,255,0.045)_1px,transparent_1px)] bg-[size:56px_56px]" />
          <div className="absolute left-8 right-8 top-[48%] h-px bg-white/30" />
          <div className="absolute left-8 right-8 top-[61%] h-px bg-white/15" />
          <div className="absolute bottom-[18%] left-0 right-0 h-12 border-y border-white/10 bg-white/[0.025]" />
          <div className="absolute left-[7%] top-[18%] flex items-center gap-2 border border-white/15 bg-black/70 px-3 py-2 text-[10px] font-black uppercase tracking-widest text-brand-light">
            <Waves size={14} aria-hidden="true" />
            Above Water
          </div>
          <div className="absolute bottom-[12%] left-[9%] flex items-center gap-2 border border-white/15 bg-black/70 px-3 py-2 text-[10px] font-black uppercase tracking-widest text-brand-light">
            <RadioTower size={14} aria-hidden="true" />
            Underwater
          </div>

          <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 56" role="img" aria-label="泳姿关键点轨迹示意">
            <polyline
              fill="none"
              points="16,31 27,27 39,28 51,30 63,29 75,31 86,34"
              stroke="rgba(255,255,255,0.75)"
              strokeLinecap="square"
              strokeWidth="0.55"
            />
            <polyline
              fill="none"
              points="34,30 42,22 49,17 57,20 65,27"
              stroke="rgba(255,255,255,0.45)"
              strokeLinecap="square"
              strokeWidth="0.5"
            />
            <polyline
              fill="none"
              points="52,31 58,40 66,45 74,43"
              stroke="rgba(255,255,255,0.36)"
              strokeLinecap="square"
              strokeWidth="0.5"
            />
            {[16, 27, 39, 51, 63, 75, 86].map((x, index) => (
              <circle cx={x} cy={[31, 27, 28, 30, 29, 31, 34][index]} fill="white" key={x} r="0.9" />
            ))}
          </svg>

          {report.overlayCues.map((cue) => (
            <div
              className={`absolute max-w-[13rem] border px-3 py-2 text-xs shadow-white-glow ${toneStyles[cue.tone]}`}
              key={cue.id}
              style={{ left: `${cue.x}%`, top: `${cue.y}%`, transform: "translate(-50%, -50%)" }}
            >
              <strong className="block text-[10px] font-black uppercase tracking-widest">{cue.label}</strong>
              <span className="mt-1 block text-[11px] leading-5 opacity-80">{cue.detail}</span>
            </div>
          ))}
        </div>

        <div className="border-t border-white/10 p-4">
          <div className="relative h-14 border border-white/10 bg-white/[0.03]">
            {report.rhythmTicks.map((tick) => (
              <div
                className="absolute top-0 h-full border-l border-white/40"
                key={tick.id}
                style={{ left: `${tick.position}%` }}
              >
                <span className={`ml-2 mt-3 inline-block border px-2 py-1 text-[10px] font-black tracking-widest ${toneStyles[tick.tone]}`}>
                  {tick.label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <aside className="grid gap-5">
        <div className="border border-white/10 bg-white/[0.035] p-5">
          <p className="text-[10px] font-black uppercase tracking-ultra text-brand-muted">Session Context</p>
          <dl className="mt-4 grid gap-3 text-sm">
            {[
              ["泳姿", strokeLabels[session.strokeType]],
              ["采集", captureModeLabels[session.captureMode]],
              ["运动员", session.swimmerLabel],
              ["场地", session.venue]
            ].map(([label, value]) => (
              <div className="flex items-center justify-between gap-4 border-b border-white/10 pb-2" key={label}>
                <dt className="text-brand-light">{label}</dt>
                <dd className="text-right font-bold text-white">{value}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="border border-white/10 bg-white/[0.035] p-5">
          <p className="text-[10px] font-black uppercase tracking-ultra text-brand-muted">Layer Status</p>
          <div className="mt-4 grid gap-3">
            {report.visualLayers.map((layer) => (
              <div className="border border-white/10 bg-black/40 p-3" key={layer.id}>
                <div className="flex items-center justify-between gap-3">
                  <strong className="text-sm text-white">{layer.label}</strong>
                  <span className="text-[10px] font-black uppercase tracking-widest text-brand-light">{layer.state}</span>
                </div>
                <p className="mt-2 text-xs leading-5 text-brand-light">{layer.detail}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="grid gap-2">
          <button className="platform-action" onClick={onOpenReport} type="button">
            <ScanLine size={16} aria-hidden="true" />
            打开分析报告
          </button>
          <button className="platform-action" onClick={onOpenTraining} type="button">
            <Timer size={16} aria-hidden="true" />
            查看训练反馈
          </button>
          <button className="platform-action" onClick={onOpenTasks} type="button">
            <Eye size={16} aria-hidden="true" />
            返回任务管理
          </button>
        </div>
      </aside>
    </div>
  );
}

export function StatusBadge({ status }: { status: SwimAnalysisJob["status"] }) {
  const label = {
    queued: "排队中",
    processing: "分析中",
    completed: "已完成",
    failed: "失败",
    canceled: "已取消"
  }[status];

  return (
    <span className="inline-flex items-center gap-2 border border-white/15 px-3 py-1 text-[10px] font-black uppercase tracking-widest text-brand-light">
      <Activity size={12} aria-hidden="true" />
      {label}
    </span>
  );
}
