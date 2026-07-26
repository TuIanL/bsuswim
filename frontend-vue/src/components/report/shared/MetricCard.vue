<script setup lang="ts">
import type { ReportMetric } from '../../../types/report'
import { metricValueLines } from './formatMetricValue'

const props = defineProps<{
  metric: ReportMetric
}>()
</script>

<template>
  <div class="metric-card" :class="metric.level ? `metric-card--${metric.level}` : ''">
    <span class="metric-card__label">{{ metric.label }}</span>
    <div class="metric-card__value">
      <strong v-for="line in metricValueLines(props.metric)" :key="line.label || String(line.value)">
        <span v-if="line.label" class="metric-card__sub-label">{{ line.label }}</span>
        {{ line.value }}<small v-if="line.unit">{{ line.unit }}</small>
      </strong>
    </div>
    <span v-if="metric.level" class="metric-card__level">{{ metric.level }}</span>
  </div>
</template>

<style scoped>
.metric-card {
  padding: 14px 18px;
  background: #f7f9fb;
  border: 1px solid #e6edf3;
  border-radius: 12px;
  min-width: 150px;
  flex: 1;
}

.metric-card__label {
  display: block;
  font-size: 13px;
  color: #5f6b7a;
  margin-bottom: 4px;
}

.metric-card__value {
  display: grid;
  gap: 5px;
}

.metric-card__value strong {
  font-size: 22px;
  font-weight: 700;
}

.metric-card__sub-label {
  display: inline-block;
  min-width: 72px;
  margin-right: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #5f6b7a;
}

.metric-card__value small {
  font-size: 14px;
  font-weight: 400;
  color: #5f6b7a;
}

.metric-card__level {
  display: inline-block;
  margin-top: 4px;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 6px;
  background: #e6edf3;
  color: #5f6b7a;
}

.metric-card--warning { border-left: 3px solid #f0ad4e; }
.metric-card--poor { border-left: 3px solid #d9534f; }
.metric-card--good { border-left: 3px solid #5cb85c; }
.metric-card--excellent { border-left: 3px solid #337ab7; }
</style>
