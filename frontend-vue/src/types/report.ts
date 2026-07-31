import type { AIInterpretationEnvelope } from '../types'

export interface NormalizedReportViewModel {
  title: string
  summary?: ReportSummaryViewModel
  overview?: ReportOverviewContext
  sections: NormalizedSection[]
  printSections?: NormalizedSection[]
  aiInterpretation?: AIInterpretationEnvelope | null
  generation_signature?: string
  provenance?: Record<string, any>
  video?: ReportVideoContext
  legacy?: boolean
}

export interface ReportVideoContext {
  playback_url?: string
  original_filename?: string
  fps?: number
  resolution?: string
}

export interface ReportOverviewContext {
  athlete?: Record<string, unknown>
  session?: Record<string, unknown>
  video?: ReportVideoContext & Record<string, unknown>
  annotation?: Record<string, unknown>
  quality?: Record<string, unknown>
  available_modules?: unknown
  analysis_boundaries?: unknown
}

export interface ReportSummaryViewModel {
  overallScore?: number
  overallLevel?: string
  radar?: { name: string; value: number }[]
  topFindings?: { title: string; severity?: string }[]
  topRecommendations?: string[]
  mainStrengths?: string[]
  mainLimitations?: string[]
}

export interface NormalizedSection {
  key: string
  type?: string
  title: string
  subtitle?: string
  summary?: string
  page_number?: number
  page_type?: string
  module_key?: string
  metrics?: ReportMetric[]
  findings?: ReportFinding[]
  recommendations?: ReportRecommendation[]
  assets?: ReportAsset[]
  charts?: ReportChart[]
  tables?: ReportTable[]
  quality_notes?: ReportQualityNote[]
  layout?: Record<string, any>
}

export interface ReportQualityNote {
  code?: string
  level?: 'info' | 'warning' | 'error'
  message: string
}

export interface ReportMetric {
  key: string
  label: string
  value: string | number | Record<string, unknown>
  unit?: string
  level?: 'excellent' | 'good' | 'normal' | 'warning' | 'poor'
}

export interface ReportFinding {
  key?: string
  title?: string
  content?: string
  evidence?: string
  severity?: 'low' | 'medium' | 'high'
  source_diagnostic?: unknown
}

export interface ReportRecommendation {
  key?: string
  title?: string
  content: string
  priority?: number
  category?: string
  source_diagnostic?: unknown
}

export interface ReportAsset {
  key: string
  type: 'image' | 'annotated_frame' | 'video_clip'
  title?: string
  url?: string
  label?: string
  value?: string | number
  caption?: string
  artifact_type?: string
  module_key?: string
  metric_keys?: string[]
  annotation_frame?: number
  source_video_frame?: number
  source_annotation_revision?: number
  metric_label?: string
  unit?: string
  selection_reason?: string
  metadata?: Record<string, unknown>
  status?: 'good' | 'warning' | 'poor'
}

export interface ReportChart {
  key: string
  type: 'line' | 'bar' | 'radar'
  title: string
  x_axis?: string[]
  y_axis_unit?: string
  series: {
    name: string
    data: number[]
    unit?: string
  }[]
}

export interface ReportTable {
  key: string
  title?: string
  columns: string[]
  rows: Array<Record<string, string | number>>
}

export type SectionKind = 'overview' | 'module' | 'trend' | 'recommendation' | 'generic' | 'kinematics_metrics' | 'kinematics_artifacts'

export type ModuleLayoutKind =
  | 'frame_grid_3'
  | 'frame_grid_2'
  | 'mixed_media'
  | 'chart_grid'
  | 'compact'
