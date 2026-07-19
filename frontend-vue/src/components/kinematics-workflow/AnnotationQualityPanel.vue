<template>
  <div class="quality-panel" v-if="quality">
    <div class="quality-head">
      <el-tag :type="qualityTagType(quality.status)" effect="dark">
        {{ qualityLabel(quality.status) }}（分 {{ quality.score ?? '-' }}）
      </el-tag>
      <div class="quality-counts">
        <span class="blocking">阻断 {{ summary.blocking_count ?? 0 }}</span>
        <span class="warning">警告 {{ summary.warning_count ?? 0 }}</span>
        <span class="info">提示 {{ summary.info_count ?? 0 }}</span>
      </div>
    </div>
    <div v-if="issues.length" class="issue-list">
      <div
        v-for="(issue, i) in issues"
        :key="i"
        class="issue-item"
        :class="issue.severity || (issue.blocking ? 'error' : 'warning')"
      >
        <div class="issue-msg">{{ issue.user_message || issue.message }}</div>
        <el-tag v-if="issue.suggested_action?.label" size="small" type="info" effect="plain">
          {{ issue.suggested_action.label }}
        </el-tag>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AnnotationQualityReport } from '../../types'

const props = defineProps<{ quality: AnnotationQualityReport | null }>()

function qualityTagType(s?: string) {
  return s === 'valid' ? 'success' : s === 'warning' ? 'warning' : s === 'invalid' ? 'danger' : 'info'
}
function qualityLabel(s?: string) {
  return s === 'valid' ? '可分析' : s === 'warning' ? '质量警告' : s === 'invalid' ? '不可分析' : '未知'
}
const summary = computed(() => props.quality?.summary ?? {})
const issues = computed(() => props.quality?.issues ?? [])
</script>

<style scoped>
.quality-head { display: flex; align-items: center; gap: 12px; }
.quality-counts { display: flex; gap: 12px; font-size: 13px; }
.blocking { color: #f56c6c; }
.warning { color: #e6a23c; }
.info { color: #909399; }
.issue-list { margin-top: 12px; display: flex; flex-direction: column; gap: 8px; }
.issue-item { display: flex; align-items: center; justify-content: space-between; padding: 8px; border-radius: 6px; background: #fafafa; }
.issue-item.error { background: #fef0f0; }
.issue-item.warning { background: #fdf6ec; }
.issue-msg { font-size: 13px; }
</style>
