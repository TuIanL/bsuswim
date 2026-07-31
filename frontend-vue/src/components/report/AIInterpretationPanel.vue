<script setup lang="ts">
import { computed } from 'vue'
import type { AIInterpretationBlock, AIInterpretationEnvelope } from '../../types'

const props = defineProps<{
  interpretation?: AIInterpretationEnvelope | null
  moduleKey: string
  print?: boolean
}>()

const content = computed(() => props.interpretation?.status === 'ready' ? props.interpretation.content : null)
const moduleExplanation = computed(() =>
  content.value?.module_explanations.find((item) => item.module_key === props.moduleKey)
)
const isOverview = computed(() => props.moduleKey === 'analysis_overview' || props.moduleKey === 'overview')
const isReview = computed(() => props.moduleKey === 'review_summary' || props.moduleKey === 'review_and_retest')
const stateText = computed(() => {
  const status = props.interpretation?.status
  if (status === 'pending') return 'AI 解读等待生成'
  if (status === 'generating') return 'AI 解读生成中'
  if (status === 'failed') return props.interpretation?.error?.message || 'AI 解读生成失败'
  if (status === 'stale') return 'AI 解读与当前报告版本不一致'
  if (status === 'not_configured') return 'AI 解读未启用'
  return ''
})

function refs(block: AIInterpretationBlock): string[] {
  return [...block.fact_refs, ...block.knowledge_refs, ...(block.evidence_refs || [])]
}
</script>

<template>
  <section
    v-if="content && (isOverview || moduleExplanation || isReview)"
    class="ai-interpretation"
    :class="{ 'ai-interpretation--print': print }"
    data-ai-interpretation-status="ready"
  >
    <header class="ai-interpretation__header">
      <div>
        <span class="ai-interpretation__label">AI 辅助解读</span>
        <h3>{{ isOverview ? '通俗总结' : isReview ? '训练重点与复测' : '模块说明' }}</h3>
      </div>
      <span v-if="isOverview" class="ai-interpretation__model">
        {{ interpretation?.trace?.model || 'AI model' }}
        <small v-if="interpretation?.trace?.execution_mode === 'visual'">视觉证据</small>
        <small v-else>文本事实</small>
      </span>
    </header>

    <div v-if="isOverview" class="ai-interpretation__body">
      <p>{{ content.plain_language_summary.text }}</p>
      <details v-if="refs(content.plain_language_summary).length" class="ai-refs">
        <summary>查看依据</summary>
        <code v-for="ref in refs(content.plain_language_summary)" :key="ref">{{ ref }}</code>
      </details>
    </div>

    <div v-else-if="moduleExplanation" class="ai-interpretation__body">
      <p>{{ moduleExplanation.text }}</p>
      <details v-if="refs(moduleExplanation).length" class="ai-refs">
        <summary>查看依据</summary>
        <code v-for="ref in refs(moduleExplanation)" :key="ref">{{ ref }}</code>
      </details>
    </div>

    <div v-else-if="isReview" class="ai-review-grid">
      <div v-if="content.priority_focus.length" class="ai-review-block">
        <h4>优先关注</h4>
        <p v-for="item in content.priority_focus" :key="item.text">{{ item.text }}</p>
      </div>
      <div v-if="content.training_suggestions.length" class="ai-review-block">
        <h4>条件式训练建议</h4>
        <article v-for="item in content.training_suggestions" :key="item.title">
          <strong>{{ item.title }}</strong>
          <p>{{ item.text }}</p>
          <small>{{ item.applicability }}</small>
          <details v-if="refs(item).length" class="ai-refs">
            <summary>查看依据</summary>
            <code v-for="ref in refs(item)" :key="ref">{{ ref }}</code>
          </details>
        </article>
      </div>
      <div v-if="content.retest_targets.length" class="ai-review-block">
        <h4>复测目标</h4>
        <p v-for="item in content.retest_targets" :key="item.metric_key">{{ item.text }}</p>
      </div>
      <div v-if="content.limitations.length" class="ai-review-block ai-review-block--limitations">
        <h4>使用边界</h4>
        <p v-for="item in content.limitations" :key="item">{{ item }}</p>
      </div>
    </div>
  </section>

  <div
    v-else-if="isOverview && interpretation && interpretation.status !== 'ready'"
    class="ai-interpretation-state"
    :data-ai-interpretation-status="interpretation.status"
  >
    <strong>AI 辅助解读</strong>
    <span>{{ stateText }}</span>
  </div>
</template>

<style scoped>
.ai-interpretation {
  margin: 0 0 20px;
  padding: 18px 20px;
  border-left: 3px solid #16826c;
  background: #f4faf8;
}

.ai-interpretation__header {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 10px;
}

.ai-interpretation__label {
  color: #16826c;
  font-size: 12px;
  font-weight: 700;
}

.ai-interpretation h3,
.ai-interpretation h4 {
  margin: 2px 0 0;
  color: #1f2d3d;
}

.ai-interpretation h3 { font-size: 17px; }
.ai-interpretation h4 { font-size: 14px; }
.ai-interpretation p { margin: 6px 0; color: #435363; line-height: 1.6; }
.ai-interpretation small { color: #6d7a86; }
.ai-interpretation__model { color: #6d7a86; font-size: 11px; }

.ai-review-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px 24px;
}

.ai-review-block article + article { margin-top: 10px; }
.ai-review-block--limitations { color: #6d5d35; }

.ai-refs { margin-top: 8px; color: #647482; font-size: 11px; }
.ai-refs summary { cursor: pointer; }
.ai-refs code { display: block; overflow-wrap: anywhere; }

.ai-interpretation-state {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin: 0 0 20px;
  padding: 10px 14px;
  border-left: 3px solid #9ba8b4;
  background: #f6f8fa;
  color: #5f6b7a;
  font-size: 13px;
}

.ai-interpretation--print {
  margin-bottom: 8px;
  padding: 10px 12px;
  font-size: 11px;
}

.ai-interpretation--print p { line-height: 1.4; }
.ai-interpretation--print .ai-review-grid { gap: 8px 14px; }

@media (max-width: 720px) {
  .ai-review-grid { grid-template-columns: 1fr; }
}

@media print {
  .ai-refs { display: none; }
}
</style>
