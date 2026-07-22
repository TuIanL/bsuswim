<template>
  <div class="kinematics-metrics-section">
    <div v-if="metrics.length === 0" class="empty-state">
      <span class="empty-text">暂无指标数据</span>
    </div>
    <div v-else class="metrics-grid">
      <div v-for="metric in metrics" :key="metric.key" class="metric-item">
        <div class="metric-header">
          <span class="metric-label">{{ metric.label }}</span>
          <span v-if="metric.level" class="metric-level" :class="metric.level">
            {{ getLevelText(metric.level) }}
          </span>
        </div>
        <div class="metric-value">
          {{ metric.value }}
          <span v-if="metric.unit" class="metric-unit">{{ metric.unit }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ReportMetric } from '../../../types/report'

defineProps<{
  metrics: ReportMetric[]
}>()

function getLevelText(level: string): string {
  const levelMap: Record<string, string> = {
    excellent: '优秀',
    good: '良好',
    normal: '一般',
    warning: '警告',
    poor: '较差'
  }
  return levelMap[level] || level
}
</script>

<style scoped>
.kinematics-metrics-section {
  padding: 8px 0;
}

.empty-state {
  text-align: center;
  padding: 16px;
  color: #909399;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.metric-item {
  padding: 12px;
  background: #f5f7fa;
  border-radius: 6px;
}

.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.metric-label {
  font-size: 13px;
  color: #606266;
}

.metric-level {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 3px;
}

.metric-level.excellent {
  background: #f0f9eb;
  color: #67c23a;
}

.metric-level.good {
  background: #ecf5ff;
  color: #409eff;
}

.metric-level.normal {
  background: #f4f4f5;
  color: #909399;
}

.metric-level.warning {
  background: #fdf6ec;
  color: #e6a23c;
}

.metric-level.poor {
  background: #fef0f0;
  color: #f56c6c;
}

.metric-value {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.metric-unit {
  font-size: 12px;
  font-weight: normal;
  color: #909399;
  margin-left: 4px;
}
</style>
