<template>
  <div class="wf-stepper">
    <div
      v-for="(step, i) in steps"
      :key="step.key"
      class="wf-step"
      :class="{ active: i === currentIndex, done: i < currentIndex }"
    >
      <div class="wf-step-dot">{{ i < currentIndex ? '✓' : i + 1 }}</div>
      <div class="wf-step-label">{{ step.label }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { WorkflowPhase } from '../../types'

const props = defineProps<{ phase: WorkflowPhase }>()

const steps = [
  { key: 'video', label: '侧面视频' },
  { key: 'annotation', label: 'CVAT 标注' },
  { key: 'quality', label: '标注质量' },
  { key: 'modules', label: '模块可用' },
  { key: 'analysis', label: '提交分析' },
  { key: 'report', label: '查看报告' }
]

const phaseOrder: WorkflowPhase[] = [
  'video_required',
  'annotation_required',
  'annotation_processing',
  'annotation_review',
  'ready_to_analyze',
  'analysis_running',
  'analysis_failed',
  'report_ready'
]

const currentIndex = computed(() => {
  const p = props.phase
  if (p === 'video_required') return 0
  if (p === 'annotation_required' || p === 'annotation_processing' || p === 'annotation_review') return 1
  if (p === 'ready_to_analyze') return 4
  if (p === 'analysis_running') return 4
  if (p === 'analysis_failed') return 4
  if (p === 'report_ready') return 5
  return 0
})
</script>

<style scoped>
.wf-stepper { display: flex; gap: 8px; flex-wrap: wrap; margin: 16px 0; }
.wf-step { display: flex; align-items: center; gap: 8px; opacity: 0.5; }
.wf-step.active, .wf-step.done { opacity: 1; }
.wf-step-dot {
  width: 26px; height: 26px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: #ebeef5; color: #909399; font-size: 13px;
}
.wf-step.active .wf-step-dot { background: #409eff; color: #fff; }
.wf-step.done .wf-step-dot { background: #67c23a; color: #fff; }
.wf-step-label { font-size: 13px; color: #303133; }
</style>
