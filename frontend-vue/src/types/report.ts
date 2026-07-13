export interface NormalizedReportViewModel {
  title: string
  summary?: ReportSummaryViewModel
  sections: NormalizedSection[]
  provenance?: Record<string, any>
  legacy?: boolean
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
  metrics?: ReportMetric[]
  findings?: ReportFinding[]
  recommendations?: ReportRecommendation[]
  assets?: ReportAsset[]
  charts?: ReportChart[]
  tables?: ReportTable[]
  layout?: Record<string, any>
}

export interface ReportMetric {
  key: string
  label: string
  value: string | number
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
  value?: string
  caption?: string
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

export type SectionKind = 'overview' | 'module' | 'trend' | 'recommendation' | 'generic'

export type ModuleLayoutKind =
  | 'frame_grid_3'
  | 'frame_grid_2'
  | 'mixed_media'
  | 'chart_grid'
  | 'compact'
