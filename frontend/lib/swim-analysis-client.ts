"use client";

import { cloneReportForSession, demoSwimReport, swimStageBlueprint } from "@/lib/swim-demo-data";
import type {
  SwimAnalysisJob,
  SwimAnalysisReport,
  SwimCreateAnalysisInput,
  SwimUploadMetadata
} from "@/lib/swim-types";

const JOBS_KEY = "zhiyong-yunshu-swim-analysis-jobs";
const REPORTS_KEY = "zhiyong-yunshu-swim-analysis-reports";
const RECENT_JOB_KEY = "zhiyong-yunshu-recent-swim-analysis-job";

export const RECENT_SWIM_ANALYSIS_JOB_EVENT = "zhiyong-yunshu-recent-swim-analysis-job-change";

type StoredReports = Record<string, SwimAnalysisReport>;

function canUseStorage() {
  return typeof window !== "undefined" && Boolean(window.localStorage);
}

function readJson<T>(key: string, fallback: T): T {
  if (!canUseStorage()) {
    return fallback;
  }

  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function writeJson<T>(key: string, value: T) {
  if (!canUseStorage()) {
    return;
  }

  window.localStorage.setItem(key, JSON.stringify(value));
}

export function formatFileSize(bytes?: number) {
  if (!bytes) {
    return "演示视频";
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function listSwimAnalysisJobs(): SwimAnalysisJob[] {
  return readJson<SwimAnalysisJob[]>(JOBS_KEY, []).sort(
    (a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt)
  );
}

export function getRecentSwimAnalysisJob(): SwimAnalysisJob | null {
  return readJson<SwimAnalysisJob | null>(RECENT_JOB_KEY, null);
}

export function rememberSwimAnalysisJob(job: SwimAnalysisJob) {
  writeJson(RECENT_JOB_KEY, job);
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(RECENT_SWIM_ANALYSIS_JOB_EVENT, { detail: job }));
  }
}

function saveJob(job: SwimAnalysisJob, report: SwimAnalysisReport) {
  const jobs = listSwimAnalysisJobs().filter((item) => item.id !== job.id);
  const reports = readJson<StoredReports>(REPORTS_KEY, {});
  reports[job.id] = report;
  writeJson(JOBS_KEY, [job, ...jobs]);
  writeJson(REPORTS_KEY, reports);
  rememberSwimAnalysisJob(job);
}

export function getSwimAnalysisJob(jobId: string): SwimAnalysisJob | null {
  return listSwimAnalysisJobs().find((job) => job.id === jobId) ?? null;
}

export function getSwimAnalysisReport(jobId?: string): SwimAnalysisReport {
  if (!jobId) {
    return demoSwimReport;
  }

  const reports = readJson<StoredReports>(REPORTS_KEY, {});
  return reports[jobId] ?? demoSwimReport;
}

export function createSwimAnalysisJob(input: SwimCreateAnalysisInput): SwimAnalysisJob {
  const now = new Date().toISOString();
  const id = `swim-${Date.now().toString(36)}`;
  const reportId = `ZY-${id.toUpperCase()}`;
  const fileName = input.file?.name ?? "demo-side-view-freestyle.mp4";
  const metadata: SwimUploadMetadata = {
    ...input.metadata,
    fileName,
    fileSize: input.file?.size
  };

  const job: SwimAnalysisJob = {
    id,
    status: "completed",
    stage: "report",
    progress: 100,
    createdAt: now,
    updatedAt: now,
    metadata,
    stages: swimStageBlueprint,
    reportId,
    source: input.demoMode || !input.file ? "demo" : "local-job"
  };

  saveJob(job, cloneReportForSession(reportId, metadata));
  return job;
}

export function seedDemoSwimJob() {
  const recent = getRecentSwimAnalysisJob();
  if (recent) {
    return recent;
  }

  return createSwimAnalysisJob({
    demoMode: true,
    metadata: {
      sessionTitle: demoSwimReport.session.sessionTitle,
      venue: demoSwimReport.session.venue,
      sessionDate: demoSwimReport.session.sessionDate,
      swimmerLabel: demoSwimReport.session.swimmerLabel,
      strokeType: demoSwimReport.session.strokeType,
      level: demoSwimReport.session.level,
      captureMode: demoSwimReport.session.captureMode
    }
  });
}
