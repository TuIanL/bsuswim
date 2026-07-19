<template>
  <div class="progress-panel">
    <div class="progress-head">
      <span>分析进度</span>
      <small v-if="attempt > 1">（第 {{ attempt }} 次尝试）</small>
      <span class="pct">{{ progress }}%</span>
    </div>
    <el-progress :percentage="progress" :status="progressStatus" />

    <ul class="step-list">
      <li v-for="step in steps" :key="step.key" class="step" :class="`step-${step.status}`">
        <el-icon v-if="step.status === 'running'" class="is-loading"><Loading /></el-icon>
        <el-icon v-else-if="step.status === 'completed'"><CircleCheck /></el-icon>
        <el-icon v-else-if="step.status === 'failed'"><CircleClose /></el-icon>
        <el-icon v-else><Minus /></el-icon>
        <span class="step-label">{{ stageLabel(step.key ?? '') }}</span>
        <span v-if="step.status === 'failed' && step.error_code" class="step-err">{{ step.error_code }}</span>
      </li>
    </ul>

    <div v-if="warnings.length" class="warnings">
      <div v-for="(w, i) in warnings" :key="i" class="warning-item">⚠ {{ w }}</div>
    </div>

     <div v-if="failed || forceFailed" class="failure-box">
       <div class="failure-line">
         <strong>失败阶段：</strong>{{ stageLabel(failedStage) }}
       </div>
       <div v-if="errorCode" class="failure-line">
         <strong>错误码：</strong><code>{{ errorCode }}</code>
       </div>
       <div v-if="errorMessage" class="failure-line failure-msg">{{ errorMessage }}</div>
       <div class="failure-actions">
         <el-button v-if="actions.includes('retry')" type="primary" :loading="busy === 'retry'" @click="$emit('retry')">重试当前任务</el-button>
         <el-button v-if="actions.includes('resubmit')" type="warning" :loading="busy === 'resubmit'" @click="$emit('resubmit')">使用当前标注重新生成</el-button>
       </div>
     </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PipelineProgress, PipelineStep } from '../../types'
import { stageLabel } from '../../utils/kinematicsWorkflow'

const props = defineProps<{
  progress: PipelineProgress | null
  status?: string
  failedStage?: string | null
  errorCode?: string | null
  errorMessage?: string | null
  actions: string[]
  busy?: 'retry' | 'resubmit' | null
  forceFailed?: boolean
}>()
const emit = defineEmits<{ (e: 'retry'): void; (e: 'resubmit'): void }>()

const steps = computed<PipelineStep[]>(() => props.progress?.steps ?? [])
const attempt = computed(() => props.progress?.attempt_count ?? 1)
const warnings = computed(() => props.progress?.warnings ?? [])
const failed = computed(() => props.status === 'failed')
const progressStatus = computed(() =>
  props.status === 'failed' ? 'exception' : props.status === 'completed' ? 'success' : undefined
)
</script>

<style scoped>
.progress-panel { padding: 12px 0; }
.progress-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.pct { margin-left: auto; font-weight: 600; }
.step-list { list-style: none; padding: 0; margin: 12px 0 0; display: flex; flex-direction: column; gap: 6px; }
.step { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #909399; }
.step-running { color: #409eff; }
.step-completed { color: #67c23a; }
.step-failed { color: #f56c6c; }
.step-err { font-size: 11px; color: #f56c6c; }
.warnings { margin-top: 10px; }
.warning-item { font-size: 12px; color: #e6a23c; }
.failure-box { margin-top: 14px; padding: 12px; background: #fef0f0; border-radius: 8px; }
.failure-line { font-size: 13px; margin-bottom: 4px; }
.failure-msg { color: #909399; }
.failure-actions { display: flex; gap: 8px; margin-top: 10px; }
</style>
