<template>
  <div class="workspace-metrics-panel">
    <template v-if="isKinematics">
      <div v-for="group in kinematicsGroups" :key="group.key" class="metric-group">
        <h4 class="group-title">{{ group.label }}</h4>
        <div class="metric-grid">
          <div
            v-for="metric in group.metrics"
            :key="metric.key"
            class="metric-card"
            :class="{ 'low-confidence': metric.availability === 'low_confidence' || metric.confidence < 1 }"
          >
            <span class="metric-name">{{ metricLabel(metric.key) }}</span>
            <strong class="metric-value">{{ metric.displayValue }}</strong>
            <span v-if="metric.unit && metric.unit !== 'ratio' && metric.unit !== 'r'" class="metric-unit">{{ metric.unit }}</span>
            <el-tag
              v-if="metric.availability !== 'available' || metric.confidence < 1"
              size="small"
              :type="metric.availability === 'low_confidence' ? 'warning' : 'info'"
              class="metric-tag"
            >
              {{ availabilityLabel(metric.availability, metric.confidence) }}
            </el-tag>
          </div>
        </div>
      </div>

      <el-collapse v-if="rawMetadata.length" class="raw-collapse">
        <el-collapse-item title="原始计算元数据" name="raw">
          <div class="raw-grid">
            <div v-for="item in rawMetadata" :key="item.key" class="raw-item">
              <span>{{ item.label }}</span>
              <code>{{ item.value }}</code>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </template>

    <template v-else>
      <div class="metric-grid">
        <div v-for="(value, key) in simpleMetrics" :key="key" class="metric-card">
          <span class="metric-name">{{ key }}</span>
          <strong class="metric-value">{{ value }}</strong>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  metrics?: Record<string, any> | null
  schemaVersion?: string | null
}>()

const isKinematics = computed(() =>
  props.schemaVersion === 'swim-analysis.annotation-kinematics.v1'
)

const CATEGORY_LABELS: Record<string, string> = {
  body_posture: '身体姿态',
  upper_limb: '上肢',
  lower_limb: '下肢',
  head_trunk: '头颈与躯干'
}

const METRIC_LABELS: Record<string, string> = {
  knee_rom_deg: '膝关节活动度',
  elbow_rom_deg: '肘关节活动度',
  kick_periodicity: '打腿周期性',
  body_angle_std_deg: '身体角度标准差',
  arm_extension_ratio: '手臂伸展比例',
  body_axis_angle_deg: '身体轴线角度',
  head_body_synchrony: '头身同步性',
  left_knee_angle_deg: '左膝角度',
  left_elbow_angle_deg: '左肘角度',
  posture_stability_cv: '姿态稳定系数',
  right_knee_angle_deg: '右膝角度',
  torso_axis_angle_deg: '躯干轴线角度',
  hip_vertical_range_px: '髋部垂直范围',
  right_elbow_angle_deg: '右肘角度',
  head_vertical_range_px: '头部垂直范围',
  left_right_kick_timing: '左右打腿时机',
  ankle_vertical_range_px: '踝部垂直范围',
  head_motion_spike_frames: '头部运动峰值帧',
  trunk_vertical_stability: '躯干垂直稳定性',
  shoulder_vertical_range_px: '肩部垂直范围',
  normalized_wrist_trajectory: '归一化手腕轨迹',
  wrist_velocity_px_per_frame: '手腕速度',
  head_shoulder_relative_offset: '头肩相对偏移'
}

interface KinematicsMetric {
  key: string
  category: string
  unit: string
  value: any
  displayValue: string
  availability: string
  confidence: number
  details?: Record<string, any>
}

function formatValue(value: any, key?: string): string {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'number') {
    return Number.isInteger(value) ? String(value) : value.toFixed(2)
  }
  if (typeof value === 'string') return value
  if (Array.isArray(value)) {
    if (key === 'head_motion_spike_frames') return value.join(', ')
    if (value.length <= 4) return `[${value.map((v) => formatValue(v)).join(', ')}]`
    return `${value.length} 个数据点`
  }
  if (typeof value === 'object') {
    // 优先提取常见组合字段
    if ('combined' in value && value.combined !== undefined) return formatValue(value.combined)
    if ('left' in value && 'right' in value) {
      return `左 ${formatValue(value.left)} / 右 ${formatValue(value.right)}`
    }
    if ('score' in value && value.score !== undefined) return formatValue(value.score)
    if ('period_frames' in value) return `${value.period_frames} 帧`
    if ('lag_frames' in value && 'phase_offset_deg' in value) {
      return `滞后 ${value.lag_frames} 帧 / ${value.phase_offset_deg}°`
    }
    if ('lag_frames' in value) return `${value.lag_frames} 帧`
    if ('spike_count' in value) return `${value.spike_count} 次`
    // 其他对象显示键值对
    return Object.entries(value)
      .filter(([, v]) => typeof v !== 'object')
      .map(([k, v]) => `${k}: ${formatValue(v)}`)
      .join(' | ')
  }
  return String(value)
}

function availabilityLabel(availability: string, confidence: number): string {
  if (availability === 'low_confidence') return '低置信度'
  if (availability === 'unavailable') return '不可用'
  if (confidence < 1) return `置信度 ${(confidence * 100).toFixed(0)}%`
  return ''
}

function metricLabel(key: string): string {
  return METRIC_LABELS[key] || key.replace(/_/g, ' ')
}

const kinematicsSummary = computed(() => {
  if (!props.metrics?.summary || typeof props.metrics.summary !== 'object') return []
  return Object.entries(props.metrics.summary).map(([key, item]: [string, any]): KinematicsMetric => {
    const value = item?.value ?? item
    return {
      key,
      category: item?.category || 'body_posture',
      unit: item?.unit || '',
      value,
      displayValue: formatValue(value, key),
      availability: item?.availability || 'available',
      confidence: item?.confidence ?? 1,
      details: item?.details
    }
  })
})

const kinematicsGroups = computed(() => {
  const grouped = new Map<string, KinematicsMetric[]>()
  for (const metric of kinematicsSummary.value) {
    if (!grouped.has(metric.category)) grouped.set(metric.category, [])
    grouped.get(metric.category)!.push(metric)
  }
  return Array.from(grouped.entries()).map(([key, metrics]) => ({
    key,
    label: CATEGORY_LABELS[key] || key,
    metrics
  }))
})

const rawMetadata = computed(() => {
  if (!props.metrics) return []
  const items = []
  if (props.metrics.calculator) {
    items.push({ key: 'calculator', label: '计算模块', value: props.metrics.calculator })
  }
  if (props.metrics.camera_view) {
    items.push({ key: 'camera_view', label: '视角', value: props.metrics.camera_view })
  }
  if (props.metrics.source?.stroke_type) {
    items.push({ key: 'stroke_type', label: '泳姿', value: props.metrics.source.stroke_type })
  }
  if (props.metrics.quality?.level) {
    items.push({ key: 'quality_level', label: '质量等级', value: props.metrics.quality.level })
  }
  if (props.metrics.quality?.computed_metric_count !== undefined) {
    items.push({ key: 'computed_count', label: '计算指标数', value: props.metrics.quality.computed_metric_count })
  }
  return items
})

const simpleMetrics = computed(() => {
  if (!props.metrics) return {}
  // 过滤掉复杂对象，只保留简单值
  return Object.fromEntries(
    Object.entries(props.metrics).filter(([, v]) => {
      if (v === null || v === undefined) return false
      const t = typeof v
      return t === 'number' || t === 'string' || t === 'boolean'
    })
  )
})
</script>

<style scoped>
.workspace-metrics-panel {
  --metric-name-color: #606266;
  --metric-value-color: #303133;
  --metric-bg: #f8fbfd;
  --metric-border: #dce6ee;
  --metric-warning-bg: #fdf6ec;
  --metric-warning-border: #f5dab1;
}

.metric-group + .metric-group {
  margin-top: 18px;
}

.group-title {
  font-size: 14px;
  color: #303133;
  margin: 0 0 10px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}

.metric-card {
  position: relative;
  padding: 12px 14px;
  border: 1px solid var(--metric-border);
  border-radius: 8px;
  background: var(--metric-bg);
  min-height: 70px;
  display: flex;
  flex-direction: column;
}

.metric-card.low-confidence {
  background: var(--metric-warning-bg);
  border-color: var(--metric-warning-border);
}

.metric-name {
  font-size: 12px;
  color: var(--metric-name-color);
  line-height: 1.4;
  margin-bottom: 6px;
}

.metric-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--metric-value-color);
  line-height: 1.3;
  word-break: break-word;
}

.metric-unit {
  font-size: 11px;
  color: #909399;
  margin-top: 4px;
}

.metric-tag {
  position: absolute;
  top: 8px;
  right: 8px;
}

.raw-collapse {
  margin-top: 16px;
}

.raw-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}

.raw-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.raw-item span {
  font-size: 12px;
  color: #909399;
}

.raw-item code {
  font-size: 12px;
  color: #606266;
  background: #f5f7fa;
  padding: 4px 8px;
  border-radius: 4px;
  word-break: break-word;
}
</style>
