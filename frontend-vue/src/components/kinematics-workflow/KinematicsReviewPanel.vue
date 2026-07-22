<template>
  <div class="kinematics-review-panel">
    <div class="panel-header">
      <h3>诊断建议</h3>
      <div class="panel-actions">
        <el-select v-model="selectedRuleSet" size="small" style="width: 180px;">
          <el-option label="侧面2D运动学" value="side_2d_kinematics_v1" />
        </el-select>
        <el-button size="small" @click="refresh" :loading="loading">刷新</el-button>
        <el-button size="small" type="primary" @click="regenerate" :loading="generating">
          重新生成
        </el-button>
      </div>
    </div>

    <div v-if="loading" class="panel-loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载诊断数据...</span>
    </div>

    <div v-else-if="generating" class="panel-loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>正在分析...</span>
    </div>

    <div v-else-if="error" class="panel-error">
      <el-alert :title="error" type="error" show-icon :closable="false" />
      <el-button size="small" @click="refresh">重试</el-button>
    </div>

    <div v-else-if="!hasFindings" class="panel-empty">
      <el-empty description="暂无诊断发现" :image-size="80" />
    </div>

    <template v-else>
      <div v-for="group in findingGroups" :key="group.severity" class="finding-group">
        <h4 class="group-title" :class="group.severity">
          {{ group.label }} ({{ group.findings.length }})
        </h4>
        <div class="findings-list">
          <div v-for="finding in group.findings" :key="finding.finding_key" class="finding-item">
            <div class="finding-header">
              <span class="finding-title">{{ finding.title }}</span>
              <el-tag :type="getSeverityType(finding.severity)" size="small">
                {{ finding.severity }}
              </el-tag>
            </div>
            <p class="finding-description">{{ finding.description }}</p>
            <div v-if="finding.recommendation" class="finding-recommendation">
              <strong>建议:</strong> {{ finding.recommendation }}
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getReviewFindings, generateReviewFindings } from '../../services/api'
import type { ReviewFinding, ReviewFindingsReadResponse } from '../../types'

const props = defineProps<{
  annotationMetricId: number
}>()

const loading = ref(false)
const generating = ref(false)
const error = ref('')
const findingsData = ref<ReviewFindingsReadResponse | null>(null)
const selectedRuleSet = ref('side_2d_kinematics_v1')

const hasFindings = computed(() => {
  return findingsData.value && findingsData.value.findings.length > 0
})

const findingGroups = computed(() => {
  if (!findingsData.value) return []
  
  const findings = findingsData.value.findings
  const groups = [
    {
      severity: 'warning',
      label: '警告',
      findings: findings.filter(f => f.severity === 'warning')
    },
    {
      severity: 'suggestion',
      label: '建议',
      findings: findings.filter(f => f.severity === 'suggestion')
    },
    {
      severity: 'info',
      label: '信息',
      findings: findings.filter(f => f.severity === 'info')
    }
  ]

  return groups.filter(g => g.findings.length > 0)
})

function getSeverityType(severity: string): 'warning' | 'info' | 'success' {
  switch (severity) {
    case 'warning': return 'warning'
    case 'suggestion': return 'info'
    case 'info': return 'success'
    default: return 'info'
  }
}

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    findingsData.value = await getReviewFindings(props.annotationMetricId, selectedRuleSet.value)
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || '加载诊断数据失败'
  } finally {
    loading.value = false
  }
}

async function regenerate() {
  generating.value = true
  try {
    await generateReviewFindings(props.annotationMetricId, selectedRuleSet.value, true)
    await refresh()
    ElMessage.success('诊断已重新生成')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '生成诊断失败')
  } finally {
    generating.value = false
  }
}

watch(selectedRuleSet, refresh)

onMounted(refresh)
</script>

<style scoped>
.kinematics-review-panel {
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
  align-items: center;
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

.finding-group {
  margin-bottom: 16px;
}

.group-title {
  font-size: 14px;
  margin: 0 0 12px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

.group-title.warning {
  color: #e6a23c;
}

.group-title.suggestion {
  color: #409eff;
}

.group-title.info {
  color: #909399;
}

.findings-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.finding-item {
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
}

.finding-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.finding-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.finding-description {
  font-size: 13px;
  color: #606266;
  margin: 0 0 8px 0;
  line-height: 1.5;
}

.finding-recommendation {
  font-size: 13px;
  color: #409eff;
  padding: 8px 12px;
  background: #ecf5ff;
  border-radius: 4px;
}

.finding-recommendation strong {
  color: #303133;
}
</style>
