<script setup lang="ts">
import { computed } from 'vue'
import type { ReportMetric } from '../../../types/report'
import { metricValueLines } from './formatMetricValue'

const props = defineProps<{ metrics: ReportMetric[] }>()

const primaryKeys: Record<string, string[]> = {
  body_posture_head_trunk: [
    'torso_axis_angle_deg', 'body_axis_angle_deg', 'hip_vertical_range_px', 'posture_stability_cv',
  ],
  upper_limb: [
    'left_elbow_angle_deg', 'right_elbow_angle_deg', 'elbow_rom_deg', 'wrist_velocity_px_per_frame',
  ],
  lower_limb: [
    'left_knee_angle_deg', 'right_knee_angle_deg', 'knee_rom_deg', 'kick_periodicity',
  ],
}

const moduleKey = computed(() => props.metrics.some((metric) => metric.key.includes('knee')) ? 'lower_limb' :
  props.metrics.some((metric) => metric.key.includes('elbow')) ? 'upper_limb' : 'body_posture_head_trunk')

const primaryMetrics = computed(() => {
  const keys = primaryKeys[moduleKey.value] ?? []
  const byKey = new Map(props.metrics.map((metric) => [metric.key, metric]))
  return keys.map((key) => byKey.get(key)).filter((metric): metric is ReportMetric =>
    Boolean(metric) && (typeof metric?.value !== 'object' || Array.isArray(metric?.value)),
  )
})

const comparisonMetrics = computed(() => props.metrics.filter((metric) =>
  metric.value && typeof metric.value === 'object' && !Array.isArray(metric.value),
))

const secondaryMetrics = computed(() => props.metrics.filter((metric) =>
  !primaryMetrics.value.some((primary) => primary.key === metric.key) &&
  !comparisonMetrics.value.some((comparison) => comparison.key === metric.key),
))

function scalarValue(metric: ReportMetric): { value: string | number; unit?: string } {
  const line = metricValueLines(metric)[0]
  return { value: line.value, unit: line.unit }
}

function comparisonLines(metric: ReportMetric) {
  const lines = metricValueLines(metric)
  const sideLines = lines.filter((line) => line.label === '左侧' || line.label === '右侧')
  return sideLines.length ? sideLines : lines
}

function comparisonWidth(metric: ReportMetric, line: { value: string | number }) {
  const lines = comparisonLines(metric)
  const numeric = lines.map((item) => Number(item.value)).filter((value) => Number.isFinite(value))
  const max = Math.max(...numeric, 1)
  const value = Number(line.value)
  return `${Math.max(8, Math.min(100, (value / max) * 100))}%`
}

function comparisonDelta(metric: ReportMetric) {
  const values = comparisonLines(metric).map((line) => Number(line.value))
  if (values.length !== 2 || values.some((value) => !Number.isFinite(value))) return ''
  const [left, right] = values
  const delta = Math.abs(left - right)
  const baseline = Math.max(Math.abs(left), Math.abs(right), 1)
  return `左右相差 ${Number((delta / baseline * 100).toFixed(1))}%`
}

function levelText(level?: string) {
  return ({ excellent: '优秀', good: '良好', normal: '一般', warning: '注意', poor: '较差' } as Record<string, string>)[level ?? ''] ?? ''
}
</script>

<template>
  <div class="metric-overview">
    <div class="metric-overview__primary">
      <div v-for="metric in primaryMetrics" :key="metric.key" class="overview-kpi" :class="metric.level ? `overview-kpi--${metric.level}` : ''">
        <span class="overview-kpi__label">{{ metric.label }}</span>
        <strong>{{ scalarValue(metric).value }}<small>{{ scalarValue(metric).unit }}</small></strong>
        <span v-if="metric.level" class="overview-kpi__level">{{ levelText(metric.level) }}</span>
      </div>
    </div>

    <div v-if="comparisonMetrics.length" class="metric-overview__comparisons">
      <div v-for="metric in comparisonMetrics" :key="metric.key" class="comparison-panel">
        <div class="comparison-panel__header">
          <span>{{ metric.label }}</span>
          <small>{{ comparisonDelta(metric) }}</small>
        </div>
        <div v-for="line in comparisonLines(metric)" :key="line.label" class="comparison-line">
          <span>{{ line.label }}</span>
          <div class="comparison-line__track"><i :style="{ width: comparisonWidth(metric, line) }"></i></div>
          <strong>{{ line.value }}<small>{{ line.unit }}</small></strong>
        </div>
      </div>
    </div>

    <details v-if="secondaryMetrics.length" class="metric-details">
      <summary>查看完整指标 <span>{{ secondaryMetrics.length }} 项</span></summary>
      <div class="metric-details__grid">
        <div v-for="metric in secondaryMetrics" :key="metric.key" class="detail-metric">
          <span>{{ metric.label }}</span>
          <strong v-for="line in metricValueLines(metric)" :key="line.label || String(line.value)">
            <em v-if="line.label">{{ line.label }}</em>{{ line.value }}<small>{{ line.unit }}</small>
          </strong>
        </div>
      </div>
    </details>
  </div>
</template>

<style scoped>
.metric-overview { margin-bottom: 20px; }
.metric-overview__primary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
.overview-kpi { min-height: 92px; padding: 14px 16px; background: #f7f9fb; border: 1px solid #e6edf3; border-radius: 10px; }
.overview-kpi__label { display: block; color: #5f6b7a; font-size: 12px; line-height: 1.35; }
.overview-kpi strong { display: block; margin-top: 8px; color: #172b3a; font-size: 22px; line-height: 1.1; }
.overview-kpi strong small, .comparison-line strong small, .detail-metric small { margin-left: 3px; color: #718096; font-size: 11px; font-weight: 400; }
.overview-kpi__level { display: inline-block; margin-top: 8px; color: #5f6b7a; font-size: 11px; }
.overview-kpi--warning { border-top: 3px solid #d99a32; }
.overview-kpi--poor { border-top: 3px solid #c6534b; }
.overview-kpi--good { border-top: 3px solid #5a9b72; }
.metric-overview__comparisons { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 12px; }
.comparison-panel { padding: 13px 15px; background: #fff; border: 1px solid #e6edf3; border-radius: 10px; }
.comparison-panel__header { display: flex; justify-content: space-between; gap: 8px; margin-bottom: 12px; color: #34495e; font-size: 13px; font-weight: 700; }
.comparison-panel__header small { color: #8a98a8; font-size: 11px; font-weight: 400; }
.comparison-line { display: grid; grid-template-columns: 34px 1fr auto; align-items: center; gap: 8px; margin-top: 8px; color: #718096; font-size: 11px; }
.comparison-line__track { height: 7px; overflow: hidden; background: #edf2f6; border-radius: 5px; }
.comparison-line__track i { display: block; height: 100%; background: #4d8ca8; border-radius: inherit; }
.comparison-line:nth-child(3) .comparison-line__track i { background: #d58b62; }
.comparison-line strong { color: #243746; font-size: 14px; white-space: nowrap; }
.metric-details { margin-top: 12px; border-top: 1px solid #edf1f4; }
.metric-details summary { padding: 12px 2px; color: #456b7c; cursor: pointer; font-size: 12px; font-weight: 700; list-style: none; }
.metric-details summary::before { content: '＋'; margin-right: 5px; }
.metric-details[open] summary::before { content: '－'; }
.metric-details summary span { margin-left: 5px; color: #94a3af; font-weight: 400; }
.metric-details__grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; padding-bottom: 4px; }
.detail-metric { min-height: 58px; padding: 10px 12px; background: #f8fafb; border-radius: 8px; }
.detail-metric > span { display: block; margin-bottom: 5px; color: #718096; font-size: 11px; }
.detail-metric strong { display: block; color: #34495e; font-size: 15px; }
.detail-metric em { margin-right: 5px; color: #718096; font-size: 11px; font-style: normal; font-weight: 400; }
@media (max-width: 800px) {
  .metric-overview__primary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .metric-overview__comparisons, .metric-details__grid { grid-template-columns: 1fr; }
}
@media print {
  .metric-details__grid { display: grid; }
  .metric-details summary { display: none; }
}
</style>
