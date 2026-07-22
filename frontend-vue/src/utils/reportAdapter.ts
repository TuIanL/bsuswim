import type { NormalizedReportViewModel, NormalizedSection } from '../types/report'

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

  const sections: NormalizedSection[] = rawSections.map((s: any) => ({
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
      key: a.key,
      type: a.type ?? 'image',
      title: a.title ?? a.label,
      url: a.url ?? a.image_url,
      label: a.label,
      value: a.value,
      caption: a.caption,
      status: a.status,
    })),
    charts: s.charts ?? [],
    tables: s.tables ?? [],
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
    provenance: report.provenance,
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
