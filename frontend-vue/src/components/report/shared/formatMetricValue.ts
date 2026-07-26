import type { ReportMetric } from '../../../types/report'

export interface MetricValueLine { label?: string; value: string | number; unit?: string }

const labels: Record<string, string> = {
  left: '左侧', right: '右侧', score: '周期性评分', period_frames: '周期长度',
  lag_frames: '左右时序差', phase_offset_deg: '相位差',
}
const units: Record<string, string> = { period_frames: '帧', lag_frames: '帧', phase_offset_deg: '°', score: '' }

function displayUnit(unit?: string): string | undefined {
  if (!unit) return undefined
  return { deg: '°', px: '像素', frame: '帧', ratio: '比值', 'px/frame': '像素/帧', r: '相关系数' }[unit] || unit
}

function formatNumber(value: unknown): string | number {
  if (typeof value !== 'number') return String(value ?? '-')
  return Number.isInteger(value) ? value : Number(value.toFixed(2))
}

export function metricValueLines(metric: ReportMetric): MetricValueLine[] {
  const value = metric.value
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return [{ value: Array.isArray(value) ? value.join(', ') : value ?? '-', unit: displayUnit(metric.unit) }]
  }
  return Object.entries(value as Record<string, unknown>).map(([key, item]) => ({
    label: labels[key] ?? key, value: formatNumber(item), unit: key in units ? units[key] : displayUnit(metric.unit),
  }))
}
