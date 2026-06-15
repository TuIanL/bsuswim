export type SwimStrokeType = "freestyle" | "backstroke" | "breaststroke" | "butterfly" | "mixed";

export type SwimCaptureMode = "dual-camera-cart" | "above-water" | "underwater" | "stitched-side-view";

export type SwimAnalysisStatus = "queued" | "processing" | "completed" | "failed" | "canceled";

export type SwimStageStatus = "pending" | "active" | "done" | "failed" | "skipped" | "canceled";

export type SwimLayerState = "demo" | "loading" | "available" | "unavailable" | "limited";

export type SwimPlatformView = "upload" | "tasks" | "job" | "workspace" | "report" | "training";

export type SwimReportSource = "demo" | "local-job" | "limited";

export type SwimMetricTone = "strong" | "watch" | "risk" | "neutral";

export interface SwimUploadMetadata {
  fileName: string;
  fileSize?: number;
  sessionTitle: string;
  venue: string;
  sessionDate: string;
  swimmerLabel: string;
  strokeType: SwimStrokeType;
  level: string;
  captureMode: SwimCaptureMode;
}

export interface SwimAnalysisStage {
  id: string;
  label: string;
  status: SwimStageStatus;
  detail: string;
  progress?: number;
}

export interface SwimAnalysisJob {
  id: string;
  status: SwimAnalysisStatus;
  stage: string;
  progress: number;
  createdAt: string;
  updatedAt: string;
  metadata: SwimUploadMetadata;
  stages: SwimAnalysisStage[];
  reportId: string;
  source: SwimReportSource;
  errorMessage?: string;
}

export interface SwimVisualLayer {
  id: string;
  label: string;
  state: SwimLayerState;
  detail: string;
}

export interface SwimOverlayCue {
  id: string;
  label: string;
  detail: string;
  x: number;
  y: number;
  tone: SwimMetricTone;
}

export interface SwimRhythmTick {
  id: string;
  label: string;
  position: number;
  tone: SwimMetricTone;
}

export interface SwimMetric {
  id: string;
  label: string;
  value: string;
  detail: string;
  trend: string;
  tone: SwimMetricTone;
}

export interface SwimDiagnostic {
  id: string;
  title: string;
  severity: "高" | "中" | "低";
  evidence: string;
  suggestion: string;
  expectedOutcome: string;
  priority: string;
}

export interface SwimTrainingRecommendation {
  id: string;
  issueId: string;
  title: string;
  learningContent: string;
  practiceTask: string;
  nextTarget: string;
  progress: {
    previous: number;
    current: number;
    target: number;
    unit: string;
  };
}

export interface SwimAnalysisReport {
  id: string;
  source: SwimReportSource;
  session: SwimUploadMetadata;
  summary: string;
  metrics: SwimMetric[];
  diagnostics: SwimDiagnostic[];
  recommendations: SwimTrainingRecommendation[];
  visualLayers: SwimVisualLayer[];
  overlayCues: SwimOverlayCue[];
  rhythmTicks: SwimRhythmTick[];
  keyFindings: string[];
}

export interface SwimCreateAnalysisInput {
  file?: File | null;
  metadata: Omit<SwimUploadMetadata, "fileName" | "fileSize">;
  demoMode?: boolean;
}
