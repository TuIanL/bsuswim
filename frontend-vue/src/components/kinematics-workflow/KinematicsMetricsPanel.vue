<template>
  <div class="kinematics-metrics-panel">
    <div class="panel-header">
      <h3>运动学指标</h3>
      <div class="panel-actions">
        <el-button size="small" @click="refresh" :loading="loading">刷新</el-button>
        <el-button size="small" type="primary" @click="save" :loading="saving" :disabled="!hasMetrics">
          保存指标
        </el-button>
      </div>
    </div>

    <div v-if="loading" class="panel-loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载指标数据...</span>
    </div>

    <div v-else-if="error" class="panel-error">
      <el-alert :title="error" type="error" show-icon :closable="false" />
      <el-button size="small" @click="refresh">重试</el-button>
    </div>

    <div v-else-if="!hasMetrics" class="panel-empty">
      <el-empty description="暂无指标数据" :image-size="80" />
    </div>

    <template v-else>
      <div v-for="group in metricGroups" :key="group.key" class="metric-group">
        <h4 class="group-title">{{ group.label }}</h4>
        <div class="metric-grid">
          <div v-for="metric in group.metrics" :key="metric.name" class="metric-item">
            <span class="metric-name">{{ metric.name }}</span>
            <span class="metric-value" :class="{ unavailable: metric.availability !== 'available' }">
              {{ metric.availability === 'available' ? `${metric.value} ${metric.unit}` : '不可用' }}
            </span>
          </div>
        </div>
      </div>

      <div v-if="persisted" class="persisted-indicator">
        <el-tag type="success" size="small">已保存</el-tag>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { calculateMetrics, getAnnotationMetrics } from '../../services/api'
import type { MetricValue, AnnotationMetricRead } from '../../types'

const props = defineProps<{
  normalizedAnnotationId: number
}>()

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const metricData = ref<AnnotationMetricRead | null>(null)
const persisted = ref(false)

const hasMetrics = computed(() => {
  return metricData.value && Object.keys(metricData.value.metrics).length > 0
})

const metricGroups = computed(() => {
  if (!metricData.value) return []
  
  const metrics = metricData.value.metrics
  const groups = [
    {
      key: 'body_posture',
      label: '身体姿态',
      metrics: Object.entries(metrics)
        .filter(([key]) => key.includes('body') || key.includes('head') || key.includes('trunk'))
        .map(([key, value]) => ({ name: key, value: value.value, unit: value.unit, availability: value.availability }))
    },
    {
      key: 'upper_limb',
      label: '上肢',
      metrics: Object.entries(metrics)
        .filter(([key]) => key.includes('arm') || key.includes('elbow') || key.includes('wrist') || key.includes('hand'))
        .map(([key, value]) => ({ name: key, value: value.value, unit: value.unit, availability: value.availability }))
    },
    {
      key: 'lower_limb',
      label: '下肢',
      metrics: Object.entries(metrics)
        .filter(([key]) => key.includes('leg') || key.includes('knee') || key.includes('ankle') || key.includes('foot'))
        .map(([key, value]) => ({ name: key, value: value.value, unit: value.unit, availability: value.availability }))
    }
  ]

  return groups.filter(g => g.metrics.length > 0)
})

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    metricData.value = await getAnnotationMetrics(props.normalizedAnnotationId)
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || '加载指标数据失败'
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const result = await calculateMetrics(props.normalizedAnnotationId, true)
    persisted.value = result.persisted
    ElMessage.success('指标已保存')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '保存指标失败')
  } finally {
    saving.value = false
  }
}

onMounted(refresh)
</script>

<style scoped>
.kinematics-metrics-panel {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  background: #fff;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.panel-actions {
  display: flex;
  gap: 8px;
}

.panel-loading,
.panel-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
  color: #909399;
}

.panel-error {
  padding: 16px;
}

.metric-group {
  margin-bottom: 16px;
}

.group-title {
  font-size: 14px;
  color: #606266;
  margin: 0 0 12px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
}

.metric-name {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.metric-value {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.metric-value.unavailable {
  color: #c0c4cc;
  font-style: italic;
}

.persisted-indicator {
  margin-top: 12px;
  text-align: right;
}
</style>
