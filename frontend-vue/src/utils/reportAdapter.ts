import type { NormalizedReportViewModel, NormalizedSection } from '../types/report'

function resolveAssetUrl(url: unknown): string | undefined {
  if (typeof url !== 'string' || !url) return undefined
  if (/^(https?:|data:|blob:)/i.test(url)) return url

  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || ''
  if (!apiBaseUrl) return url

  return new URL(url, `${apiBaseUrl.replace(/\/$/, '')}/`).toString()
}

const chartPresentation: Record<string, { title: string; caption: string }> = {
  'body_posture.chart.angle_timeseries': { title: '身体轴角变化', caption: '观察躯干轴和身体轴随视频帧的角度变化，曲线越平稳表示姿态控制越稳定。' },
  'body_posture.chart.hip_trajectory': { title: '髋部垂直轨迹', caption: '观察髋部相对身体长度的上下波动，轨迹越集中表示髋部支撑越稳定。' },
  'upper_limb.chart.elbow_angle_timeseries': { title: '左右肘角度变化', caption: '对比左右肘角度随视频帧的变化，用于观察屈曲、伸展和左右差异。' },
  'upper_limb.chart.joint_trajectories': { title: '上肢关节轨迹', caption: '展示左右腕部相对身体的运动路径，用于观察划臂轨迹是否连续、对称。' },
  'lower_limb.chart.knee_angle_timeseries': { title: '左右膝角度变化', caption: '观察左右膝角度随视频帧的变化，用于判断打腿屈伸和节奏。' },
  'lower_limb.chart.joint_trajectories': { title: '下肢关节轨迹', caption: '展示下肢关节相对身体的运动路径，用于观察打腿幅度和轨迹稳定性。' },
  'overview.chart.range_comparison': { title: '关键活动范围对比', caption: '把关节活动范围、身体垂直波动和身体轴角范围放在一起比较，快速定位波动较大的指标。' },
  'overview.chart.stability_radar': { title: '运动稳定性雷达图', caption: '从姿态、上肢、下肢节奏和躯干控制等维度概览稳定性；缺失维度会标为不可用。' },
}

function normalizeLegacyReport(report: Record<string, any>): NormalizedReportViewModel {
  const sections: NormalizedSection[] = []

  const legacyMetrics = report.metrics
  if (legacyMetrics && typeof legacyMetrics === 'object') {
    sections.push({
      key: 'legacy_metrics',
      title: '关键指标',
      metrics: Object.entries(legacyMetrics)
        .filter(([, v]) => typeof v === 'number' || typeof v === 'string')
        .map(([key, value]) => ({
          key,
          label: key,
          value: String(value),
        })),
    })
  }

  const legacyDiagnostics = report.diagnostics
  if (Array.isArray(legacyDiagnostics) && legacyDiagnostics.length > 0) {
    const findings = legacyDiagnostics.map((d: any, i: number) => ({
      key: d.code ?? `legacy_finding_${i}`,
      title: d.title ?? '诊断发现',
      evidence: d.evidence ?? '',
      content: d.evidence ?? d.title ?? '',
      severity: (d.severity ?? 'medium') as 'low' | 'medium' | 'high',
      source_diagnostic: d,
    }))

    const recommendations = legacyDiagnostics
      .filter((d: any) => d.suggestion || d.recommendation)
      .map((d: any, i: number) => ({
        key: d.code ?? `legacy_rec_${i}`,
        title: d.title ? `${d.title}改进建议` : '改进建议',
        content: d.suggestion ?? d.recommendation,
        severity: (d.severity ?? 'medium') as 'low' | 'medium' | 'high',
        source_diagnostic: d,
      }))

    sections.push({
      key: 'legacy_diagnostics',
      title: '诊断结果与训练建议',
      findings,
      recommendations,
    })
  }

  const legacyRecs = report.recommendations
  if (Array.isArray(legacyRecs) && legacyRecs.length > 0) {
    const existingKeys = new Set(sections.map((s) => s.key))
    if (!existingKeys.has('legacy_diagnostics')) {
      sections.push({
        key: 'legacy_recommendations',
        title: '训练建议',
        recommendations: legacyRecs.map((r: any, i: number) => ({
          key: `legacy_rec_${i}`,
          content: typeof r === 'string' ? r : r.title ?? '',
        })),
      })
    }
  }

  return {
    title: report.summary?.title ?? '分析报告',
    summary: {
      overallScore: report.summary?.overall_score ?? undefined,
      radar: report.charts?.radar ?? [],
      topFindings: report.summary?.top_findings ?? [],
      topRecommendations: report.summary?.top_recommendations ?? [],
    },
    sections,
    provenance: report.provenance ?? report.provenance,
    legacy: true,
  }
}

function normalizeSwimReportV1(report: Record<string, any>): NormalizedReportViewModel {
  const rawSections: any[] = report.sections ?? []

  const sections: NormalizedSection[] = rawSections
    .filter((s: any) => s.page_type !== 'analysis_overview')
    .map((s: any) => ({
    key: s.key,
    type: s.type,
    title: s.title ?? '',
    page_number: s.page_number,
    page_type: s.page_type,
    module_key: s.module_key,
    subtitle: s.subtitle,
    summary: s.summary,
    metrics: (s.metrics ?? []).map((m: any) => ({
      key: m.key,
      label: m.label ?? m.key,
      value: m.value,
      unit: m.unit,
      level: m.level ?? m.evaluation,
    })),
    findings: (s.findings ?? []).map((f: any) => ({
      title: f.title,
      content: f.content ?? f.description,
      evidence: f.evidence,
      severity: f.severity,
    })),
    recommendations: (s.recommendations ?? []).map((r: any) => ({
      title: r.title,
      content: r.content ?? r.description,
      category: r.category,
    })),
    assets: (s.assets ?? []).map((a: any) => ({
      ...(chartPresentation[a.key] ?? {}),
      key: a.key,
      type: a.type ?? 'image',
      title: chartPresentation[a.key]?.title ?? a.title ?? a.label,
      url: resolveAssetUrl(a.absolute_url ?? a.url ?? a.image_url),
      label: a.label,
      value: a.value,
      caption: chartPresentation[a.key]?.caption ?? a.caption,
      artifact_type: a.artifact_type,
      module_key: a.module_key,
      metric_keys: a.metric_keys ?? [],
      annotation_frame: a.annotation_frame,
      source_video_frame: a.source_video_frame,
      source_annotation_revision: a.source_annotation_revision,
      metric_label: a.metric_label ?? a.metadata?.metric_label,
      unit: a.unit ?? a.metadata?.unit,
      selection_reason: a.selection_reason ?? a.metadata?.selection_reason,
      metadata: a.metadata,
      status: a.status,
    })),
    charts: s.charts ?? [],
    tables: s.tables ?? [],
    quality_notes: s.quality_notes ?? [],
    }))

  return {
    title: report.summary?.title ?? report.title ?? '游泳专项技术分析报告',
    generation_signature: report.generation_signature,
    summary: {
      overallScore: report.summary?.overall_score ?? undefined,
      overallLevel: report.summary?.overall_level,
      radar: report.charts?.radar ?? report.summary?.radar ?? [],
      topFindings: report.summary?.top_findings ?? [],
      topRecommendations: report.summary?.top_recommendations ?? [],
      mainStrengths: report.summary?.main_strengths ?? [],
      mainLimitations: report.summary?.main_limitations ?? [],
    },
    sections,
    overview: report.context ?? report.overview,
    provenance: report.provenance,
    video: report.context?.video ?? report.video,
  }
}

export function normalizeReportData(raw: any): NormalizedReportViewModel {
  const report = raw.report ?? raw

  const isSwimReportV1 =
    report.schema_version === 'swim-report.v1' || Array.isArray(report.sections)

  if (isSwimReportV1) {
    return normalizeSwimReportV1(report)
  }

  return normalizeLegacyReport(report)
}
