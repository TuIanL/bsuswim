"use client";

import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  ClipboardCheck,
  FileVideo,
  Plus,
  RefreshCw,
  Upload
} from "lucide-react";
import { useEffect, useMemo, useState, type ChangeEvent, type FormEvent } from "react";
import {
  captureModeLabels,
  demoSwimReport,
  strokeLabels
} from "@/lib/swim-demo-data";
import {
  createSwimAnalysisJob,
  formatFileSize,
  getRecentSwimAnalysisJob,
  getSwimAnalysisJob,
  getSwimAnalysisReport,
  listSwimAnalysisJobs,
  RECENT_SWIM_ANALYSIS_JOB_EVENT,
  seedDemoSwimJob
} from "@/lib/swim-analysis-client";
import type {
  SwimAnalysisJob,
  SwimCaptureMode,
  SwimCreateAnalysisInput,
  SwimPlatformView,
  SwimStrokeType,
  SwimUploadMetadata
} from "@/lib/swim-types";
import { PlatformPageHeader, PlatformPanel, PlatformShell } from "@/components/platform/PlatformShell";
import { StatusBadge, SwimVisualWorkspace } from "@/components/platform/SwimVisualWorkspace";

const today = new Date().toISOString().slice(0, 10);

const defaultForm: SwimCreateAnalysisInput["metadata"] = {
  sessionTitle: "自由泳连续侧面训练",
  venue: "北京体育大学游泳馆",
  sessionDate: today,
  swimmerLabel: "运动员 A",
  strokeType: "freestyle",
  level: "专项提高",
  captureMode: "dual-camera-cart"
};

function isView(value: string | null): value is SwimPlatformView {
  return Boolean(value && ["upload", "tasks", "job", "workspace", "report", "training"].includes(value));
}

export function SwimPlatformApp() {
  const [view, setView] = useState<SwimPlatformView>("upload");
  const [activeJobId, setActiveJobId] = useState<string | undefined>();
  const [jobs, setJobs] = useState<SwimAnalysisJob[]>([]);

  const refreshJobs = () => setJobs(listSwimAnalysisJobs());

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const nextView = params.get("view");
    const jobId = params.get("job") ?? undefined;
    if (isView(nextView)) {
      setView(nextView);
    }
    if (jobId) {
      setActiveJobId(jobId);
    }
    refreshJobs();

    const onRecent = () => refreshJobs();
    window.addEventListener(RECENT_SWIM_ANALYSIS_JOB_EVENT, onRecent);
    window.addEventListener("storage", onRecent);
    return () => {
      window.removeEventListener(RECENT_SWIM_ANALYSIS_JOB_EVENT, onRecent);
      window.removeEventListener("storage", onRecent);
    };
  }, []);

  const activeJob = useMemo(() => {
    if (activeJobId) {
      return getSwimAnalysisJob(activeJobId);
    }
    return getRecentSwimAnalysisJob();
  }, [activeJobId]);

  const report = getSwimAnalysisReport(activeJob?.id);

  const navigate = (nextView: SwimPlatformView, jobId = activeJob?.id) => {
    setView(nextView);
    if (jobId) {
      setActiveJobId(jobId);
    }
    const params = new URLSearchParams({ view: nextView });
    if (jobId) {
      params.set("job", jobId);
    }
    window.history.pushState({}, "", `/platform?${params.toString()}`);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleCreated = (job: SwimAnalysisJob) => {
    refreshJobs();
    navigate("job", job.id);
  };

  let content;
  if (view === "tasks") {
    content = <TasksView jobs={jobs} onRefresh={refreshJobs} onNavigate={navigate} />;
  } else if (view === "job") {
    content = <JobView job={activeJob} onNavigate={navigate} />;
  } else if (view === "workspace") {
    content = (
      <WorkspaceView
        job={activeJob}
        report={report}
        onNavigate={navigate}
        onSeedDemo={() => {
          const job = seedDemoSwimJob();
          refreshJobs();
          navigate("workspace", job.id);
        }}
      />
    );
  } else if (view === "report") {
    content = <ReportView job={activeJob} report={report} onNavigate={navigate} />;
  } else if (view === "training") {
    content = <TrainingView job={activeJob} report={report} onNavigate={navigate} />;
  } else {
    content = <UploadView onCreated={handleCreated} onOpenTasks={() => navigate("tasks")} />;
  }

  return (
    <PlatformShell activeView={view} onNavigate={navigate}>
      {content}
    </PlatformShell>
  );
}

function UploadView({ onCreated, onOpenTasks }: { onCreated: (job: SwimAnalysisJob) => void; onOpenTasks: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [metadata, setMetadata] = useState(defaultForm);
  const canSubmit = metadata.sessionTitle && metadata.venue && metadata.sessionDate && metadata.swimmerLabel;

  const update = (key: keyof typeof metadata, value: string) => {
    setMetadata((current) => ({ ...current, [key]: value }));
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canSubmit) {
      return;
    }
    onCreated(createSwimAnalysisJob({ file, metadata, demoMode: !file }));
  };

  const handleFile = (event: ChangeEvent<HTMLInputElement>) => {
    setFile(event.target.files?.[0] ?? null);
  };

  return (
    <>
      <PlatformPageHeader
        eyebrow="New Swim Analysis"
        title="上传训练视频"
        description="从训练视频、泳姿信息和采集模式开始，生成可演示的智泳云枢分析任务。当前版本可无后端运行，结果会标注为本地演示。"
        action={
          <button className="platform-action" onClick={onOpenTasks} type="button">
            查看任务
            <ArrowRight size={16} aria-hidden="true" />
          </button>
        }
      />

      <form className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_24rem]" onSubmit={submit}>
        <PlatformPanel className="p-5 sm:p-6">
          <label className="flex min-h-[18rem] cursor-pointer flex-col items-center justify-center border border-dashed border-white/20 bg-black/40 p-6 text-center transition hover:border-white/60">
            <Upload size={34} strokeWidth={1.4} aria-hidden="true" />
            <strong className="mt-5 text-lg font-black tracking-widest">选择泳姿训练视频</strong>
            <span className="mt-3 max-w-md text-sm leading-7 text-brand-light">
              支持本地视频文件。若不选择文件，将使用连续侧面自由泳样例生成演示任务。
            </span>
            <span className="mt-5 border border-white bg-white px-5 py-3 text-xs font-black uppercase tracking-widest text-black">
              Browse Video
            </span>
            <input accept="video/*" className="sr-only" onChange={handleFile} type="file" />
          </label>

          <div className="mt-5 border border-white/10 bg-white/[0.03] p-4">
            <p className="text-[10px] font-black uppercase tracking-ultra text-brand-muted">Selected Source</p>
            <div className="mt-3 flex items-center gap-3">
              <FileVideo className="shrink-0 text-white" size={22} aria-hidden="true" />
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-white">{file?.name ?? "demo-side-view-freestyle.mp4"}</p>
                <p className="mt-1 text-xs text-brand-light">{formatFileSize(file?.size)}</p>
              </div>
            </div>
          </div>
        </PlatformPanel>

        <PlatformPanel className="p-5 sm:p-6">
          <p className="text-[10px] font-black uppercase tracking-ultra text-brand-muted">Session Metadata</p>
          <div className="mt-5 grid gap-4">
            <Field label="训练标题" value={metadata.sessionTitle} onChange={(value) => update("sessionTitle", value)} />
            <Field label="泳池/场地" value={metadata.venue} onChange={(value) => update("venue", value)} />
            <Field label="运动员" value={metadata.swimmerLabel} onChange={(value) => update("swimmerLabel", value)} />
            <Field label="日期" type="date" value={metadata.sessionDate} onChange={(value) => update("sessionDate", value)} />
            <SelectField
              label="泳姿"
              value={metadata.strokeType}
              onChange={(value) => update("strokeType", value)}
              options={strokeLabels}
            />
            <Field label="水平" value={metadata.level} onChange={(value) => update("level", value)} />
            <SelectField
              label="采集模式"
              value={metadata.captureMode}
              onChange={(value) => update("captureMode", value)}
              options={captureModeLabels}
            />
          </div>

          <button
            className="mt-6 inline-flex min-h-12 w-full items-center justify-center gap-2 border border-white bg-white px-5 text-xs font-black uppercase tracking-widest text-black transition hover:bg-transparent hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
            disabled={!canSubmit}
            type="submit"
          >
            <Plus size={16} aria-hidden="true" />
            开始分析
          </button>
          {!canSubmit ? <p className="mt-3 text-xs leading-5 text-brand-light">请补全训练标题、场地、日期和运动员。</p> : null}
        </PlatformPanel>
      </form>
    </>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text"
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
}) {
  return (
    <label className="block">
      <span className="text-[10px] font-black uppercase tracking-widest text-brand-light">{label}</span>
      <input
        className="mt-2 min-h-11 w-full border border-white/15 bg-black px-3 text-sm font-semibold text-white outline-none transition focus:border-white"
        onChange={(event) => onChange(event.target.value)}
        type={type}
        value={value}
      />
    </label>
  );
}

function SelectField<T extends string>({
  label,
  value,
  onChange,
  options
}: {
  label: string;
  value: T;
  onChange: (value: T) => void;
  options: Record<T, string>;
}) {
  return (
    <label className="block">
      <span className="text-[10px] font-black uppercase tracking-widest text-brand-light">{label}</span>
      <select
        className="mt-2 min-h-11 w-full border border-white/15 bg-black px-3 text-sm font-semibold text-white outline-none transition focus:border-white"
        onChange={(event) => onChange(event.target.value as T)}
        value={value}
      >
        {Object.entries(options).map(([key, labelText]) => (
          <option key={key} value={key}>
            {labelText as string}
          </option>
        ))}
      </select>
    </label>
  );
}

function TasksView({
  jobs,
  onRefresh,
  onNavigate
}: {
  jobs: SwimAnalysisJob[];
  onRefresh: () => void;
  onNavigate: (view: SwimPlatformView, jobId?: string) => void;
}) {
  return (
    <>
      <PlatformPageHeader
        eyebrow="Analysis Tasks"
        title="任务管理"
        description="追踪本地演示分析任务，查看状态、训练会话信息和结果入口。后续接入后端后，这里会承接真实队列与算法进度。"
        action={
          <button className="platform-action" onClick={onRefresh} type="button">
            <RefreshCw size={16} aria-hidden="true" />
            刷新任务
          </button>
        }
      />

      {jobs.length ? (
        <div className="grid gap-4">
          {jobs.map((job) => (
            <PlatformPanel className="p-5" key={job.id}>
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-3">
                    <StatusBadge status={job.status} />
                    <span className="text-[10px] font-black uppercase tracking-widest text-brand-muted">{job.reportId}</span>
                  </div>
                  <h2 className="mt-3 text-2xl font-black tracking-widest text-white">{job.metadata.sessionTitle}</h2>
                  <p className="mt-2 text-sm leading-6 text-brand-light">
                    {job.metadata.swimmerLabel} · {strokeLabels[job.metadata.strokeType]} · {captureModeLabels[job.metadata.captureMode]} · {job.metadata.venue}
                  </p>
                </div>
                <div className="grid gap-2 sm:grid-cols-3 lg:w-[28rem]">
                  <button className="platform-action" onClick={() => onNavigate("job", job.id)} type="button">
                    状态
                  </button>
                  <button className="platform-action" onClick={() => onNavigate("workspace", job.id)} type="button">
                    工作台
                  </button>
                  <button className="platform-action" onClick={() => onNavigate("report", job.id)} type="button">
                    报告
                  </button>
                </div>
              </div>
            </PlatformPanel>
          ))}
        </div>
      ) : (
        <EmptyState
          title="还没有分析任务"
          body="先上传训练视频，或直接创建演示任务。"
          actionLabel="新建分析"
          onAction={() => onNavigate("upload")}
        />
      )}
    </>
  );
}

function JobView({
  job,
  onNavigate
}: {
  job?: SwimAnalysisJob | null;
  onNavigate: (view: SwimPlatformView, jobId?: string) => void;
}) {
  if (!job) {
    return (
      <EmptyState
        title="没有找到任务"
        body="当前浏览器没有可用的任务上下文，可以返回任务管理或创建新的演示任务。"
        actionLabel="返回任务管理"
        onAction={() => onNavigate("tasks")}
      />
    );
  }

  return (
    <>
      <PlatformPageHeader
        eyebrow="Job Status"
        title="分析状态"
        description="任务详情页展示上传、同步、拼接、姿态、划水分段、指标和报告生成等游泳分析阶段。"
        action={<StatusBadge status={job.status} />}
      />
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <PlatformPanel className="p-5">
          <div className="flex items-center justify-between gap-4 border-b border-white/10 pb-4">
            <div>
              <h2 className="text-2xl font-black tracking-widest text-white">{job.metadata.sessionTitle}</h2>
              <p className="mt-2 text-sm text-brand-light">{job.metadata.fileName} · {formatFileSize(job.metadata.fileSize)}</p>
            </div>
            <strong className="text-4xl font-black text-white">{job.progress}%</strong>
          </div>
          <div className="mt-5 grid gap-3">
            {job.stages.map((stage) => (
              <div className="grid gap-3 border border-white/10 bg-black/30 p-4 sm:grid-cols-[12rem_1fr_auto] sm:items-center" key={stage.id}>
                <div className="flex items-center gap-2">
                  {stage.status === "done" ? <CheckCircle2 size={16} aria-hidden="true" /> : <AlertTriangle size={16} aria-hidden="true" />}
                  <strong className="text-sm text-white">{stage.label}</strong>
                </div>
                <p className="text-sm leading-6 text-brand-light">{stage.detail}</p>
                <span className="text-[10px] font-black uppercase tracking-widest text-brand-muted">{stage.status}</span>
              </div>
            ))}
          </div>
        </PlatformPanel>

        <div className="grid gap-3 self-start">
          <button className="platform-action" onClick={() => onNavigate("workspace", job.id)} type="button">
            打开视觉工作台
            <ArrowRight size={16} aria-hidden="true" />
          </button>
          <button className="platform-action" onClick={() => onNavigate("report", job.id)} type="button">
            打开分析报告
            <ArrowRight size={16} aria-hidden="true" />
          </button>
          <button className="platform-action" onClick={() => onNavigate("training", job.id)} type="button">
            训练反馈
            <ArrowRight size={16} aria-hidden="true" />
          </button>
        </div>
      </div>
    </>
  );
}

function WorkspaceView({
  job,
  report,
  onNavigate,
  onSeedDemo
}: {
  job?: SwimAnalysisJob | null;
  report: typeof demoSwimReport;
  onNavigate: (view: SwimPlatformView, jobId?: string) => void;
  onSeedDemo: () => void;
}) {
  if (!job) {
    return (
      <>
        <PlatformPageHeader
          eyebrow="Visual Workspace"
          title="演示工作台"
          description="当前没有任务上下文，可直接打开智泳云枢样例，查看侧面视频、关键点、节奏线和图层状态的演示体验。"
          action={
            <button className="platform-action" onClick={onSeedDemo} type="button">
              载入演示任务
            </button>
          }
        />
        <SwimVisualWorkspace
          report={demoSwimReport}
          onOpenReport={() => onNavigate("report")}
          onOpenTraining={() => onNavigate("training")}
          onOpenTasks={() => onNavigate("tasks")}
        />
      </>
    );
  }

  return (
    <>
      <PlatformPageHeader
        eyebrow="Visual Workspace"
        title="视觉分析工作台"
        description="围绕连续侧面视频组织关键点、节奏、身体线条和训练建议入口。真实算法未接入的模块会保留清晰的样例或有限状态。"
      />
      <SwimVisualWorkspace
        job={job}
        report={report}
        onOpenReport={() => onNavigate("report", job.id)}
        onOpenTraining={() => onNavigate("training", job.id)}
        onOpenTasks={() => onNavigate("tasks", job.id)}
      />
    </>
  );
}

function ReportView({
  job,
  report,
  onNavigate
}: {
  job?: SwimAnalysisJob | null;
  report: typeof demoSwimReport;
  onNavigate: (view: SwimPlatformView, jobId?: string) => void;
}) {
  const session = job?.metadata ?? report.session;
  return (
    <>
      <PlatformPageHeader
        eyebrow="Performance Report"
        title="泳姿分析报告"
        description="把视频结果整理为评分、节奏、对称性、身体线条诊断和可执行训练建议。"
        action={
          <button className="platform-action" onClick={() => onNavigate("training", job?.id)} type="button">
            查看训练反馈
            <ArrowRight size={16} aria-hidden="true" />
          </button>
        }
      />

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="grid gap-5">
          <PlatformPanel className="p-5">
            <p className="text-[10px] font-black uppercase tracking-ultra text-brand-muted">Report Source</p>
            <h2 className="mt-3 text-2xl font-black tracking-widest text-white">{session.sessionTitle}</h2>
            <p className="mt-3 text-sm leading-7 text-brand-light">{report.summary}</p>
            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              {report.metrics.map((metric) => (
                <MetricCard metric={metric} key={metric.id} />
              ))}
            </div>
          </PlatformPanel>

          <PlatformPanel className="p-5">
            <p className="text-[10px] font-black uppercase tracking-ultra text-brand-muted">Technique Diagnostics</p>
            <div className="mt-5 grid gap-4">
              {report.diagnostics.map((diagnostic) => (
                <article className="border border-white/10 bg-black/35 p-4" key={diagnostic.id}>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <h3 className="text-lg font-black tracking-widest text-white">{diagnostic.title}</h3>
                    <span className="border border-white/15 px-3 py-1 text-[10px] font-black uppercase tracking-widest text-brand-light">
                      {diagnostic.severity} · {diagnostic.priority}
                    </span>
                  </div>
                  <p className="mt-3 text-sm leading-7 text-brand-light">{diagnostic.evidence}</p>
                  <p className="mt-3 text-sm leading-7 text-white">{diagnostic.suggestion}</p>
                  <p className="mt-2 text-xs leading-5 text-brand-muted">{diagnostic.expectedOutcome}</p>
                </article>
              ))}
            </div>
          </PlatformPanel>
        </div>

        <aside className="grid gap-5 self-start">
          <PlatformPanel className="p-5">
            <p className="text-[10px] font-black uppercase tracking-ultra text-brand-muted">Key Findings</p>
            <ul className="mt-4 grid gap-3">
              {report.keyFindings.map((finding) => (
                <li className="border-l border-white/30 pl-3 text-sm leading-6 text-brand-light" key={finding}>
                  {finding}
                </li>
              ))}
            </ul>
          </PlatformPanel>
          <button className="platform-action" onClick={() => onNavigate("workspace", job?.id)} type="button">
            返回视觉工作台
          </button>
        </aside>
      </div>
    </>
  );
}

function TrainingView({
  job,
  report,
  onNavigate
}: {
  job?: SwimAnalysisJob | null;
  report: typeof demoSwimReport;
  onNavigate: (view: SwimPlatformView, jobId?: string) => void;
}) {
  return (
    <>
      <PlatformPageHeader
        eyebrow="Training Loop"
        title="训练反馈闭环"
        description="把诊断问题转成下一次训练可执行的练习任务、目标和进度。"
        action={
          <button className="platform-action" onClick={() => onNavigate("report", job?.id)} type="button">
            返回报告
          </button>
        }
      />
      <div className="grid gap-5 lg:grid-cols-2">
        {report.recommendations.map((item) => (
          <PlatformPanel className="p-5" key={item.id}>
            <p className="text-[10px] font-black uppercase tracking-ultra text-brand-muted">{item.issueId}</p>
            <h2 className="mt-3 text-2xl font-black tracking-widest text-white">{item.title}</h2>
            <p className="mt-4 text-sm leading-7 text-brand-light">{item.learningContent}</p>
            <p className="mt-3 text-sm leading-7 text-white">{item.practiceTask}</p>
            <p className="mt-3 text-sm leading-7 text-brand-light">{item.nextTarget}</p>
            <div className="mt-5 h-3 border border-white/10 bg-black">
              <div
                className="h-full bg-white"
                style={{
                  width: `${Math.min(100, (item.progress.current / item.progress.target) * 100)}%`
                }}
              />
            </div>
            <div className="mt-3 flex justify-between text-xs font-bold text-brand-light">
              <span>上次 {item.progress.previous}{item.progress.unit}</span>
              <span>当前 {item.progress.current}{item.progress.unit}</span>
              <span>目标 {item.progress.target}{item.progress.unit}</span>
            </div>
          </PlatformPanel>
        ))}
      </div>
    </>
  );
}

function MetricCard({ metric }: { metric: typeof demoSwimReport.metrics[number] }) {
  return (
    <article className="border border-white/10 bg-black/40 p-4">
      <p className="text-[10px] font-black uppercase tracking-widest text-brand-muted">{metric.label}</p>
      <strong className="mt-3 block text-3xl font-black text-white">{metric.value}</strong>
      <p className="mt-2 text-xs leading-5 text-brand-light">{metric.detail}</p>
      <span className="mt-3 inline-block text-[10px] font-black uppercase tracking-widest text-white">{metric.trend}</span>
    </article>
  );
}

function EmptyState({
  title,
  body,
  actionLabel,
  onAction
}: {
  title: string;
  body: string;
  actionLabel: string;
  onAction: () => void;
}) {
  return (
    <PlatformPanel className="flex min-h-[24rem] flex-col items-center justify-center p-8 text-center">
      <BarChart3 size={38} strokeWidth={1.3} aria-hidden="true" />
      <h1 className="mt-5 text-3xl font-black tracking-widest text-white">{title}</h1>
      <p className="mt-4 max-w-md text-sm leading-7 text-brand-light">{body}</p>
      <button className="platform-action mt-6" onClick={onAction} type="button">
        <ClipboardCheck size={16} aria-hidden="true" />
        {actionLabel}
      </button>
    </PlatformPanel>
  );
}
