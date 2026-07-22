import type {
  NormalizedSection,
  SectionKind,
  ModuleLayoutKind,
} from '../types/report'

const TECHNICAL_MODULE_KEYS = new Set([
  'body_position',
  'arm_entry',
  'catch_pull',
  'leg_kick',
])

const RECOMMENDATION_KEYS = new Set([
  'recommendations',
  'recommendation',
])

const OVERVIEW_KEYS = new Set([
  'overview',
])

const TREND_KEYS = new Set([
  'efficiency',
  'trends',
  'trend',
])

export function resolveSectionKind(section: NormalizedSection): SectionKind {
  // Check for 5-page kinematics report section types
  if (section.page_type) {
    if (section.page_type === 'body_posture_head_trunk' || 
        section.page_type === 'upper_limb' || 
        section.page_type === 'lower_limb') {
      return 'kinematics_metrics'
    }
    if (section.page_type === 'review_summary') {
      return 'kinematics_artifacts'
    }
  }

  if (section.type) {
    if (section.type === 'overview') return 'overview'
    if (section.type === 'trend_charts') return 'trend'
    if (section.type === 'recommendation') return 'recommendation'
    if (section.type === 'evidence_frames' || section.type === 'module') return 'module'
    if (section.type === 'kinematics_metrics') return 'kinematics_metrics'
    if (section.type === 'kinematics_artifacts') return 'kinematics_artifacts'
  }

  if (TECHNICAL_MODULE_KEYS.has(section.key)) return 'module'
  if (RECOMMENDATION_KEYS.has(section.key)) return 'recommendation'
  if (OVERVIEW_KEYS.has(section.key)) return 'overview'
  if (TREND_KEYS.has(section.key)) return 'trend'

  const hasCharts = (section.charts?.length ?? 0) > 0
  const hasAssets = (section.assets?.length ?? 0) > 0
  const hasFindings = (section.findings?.length ?? 0) > 0
  const hasMetrics = (section.metrics?.length ?? 0) > 0

  if (hasCharts && !hasAssets && !hasFindings && !hasMetrics) return 'trend'

  if (hasAssets || hasFindings || hasMetrics) return 'module'

  return 'generic'
}

export function resolveModuleLayout(section: NormalizedSection): ModuleLayoutKind {
  const assetCount = section.assets?.length ?? 0
  const chartCount = section.charts?.length ?? 0

  if (assetCount >= 3 && chartCount === 0) return 'frame_grid_3'
  if (assetCount === 2 && chartCount === 0) return 'frame_grid_2'
  if (assetCount > 0 && chartCount > 0) return 'mixed_media'
  if (chartCount >= 1 && assetCount === 0) return 'chart_grid'

  return 'compact'
}
