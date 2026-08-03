<script setup lang="ts">
import { computed } from 'vue'
import type { AIInterpretationEnvelope } from '../../types'
import InterpretationBlockView from './InterpretationBlockView.vue'

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
      <InterpretationBlockView
        :block="content.plain_language_summary"
        :references="interpretation?.references"
        :print="print"
      />
    </div>

    <div v-else-if="moduleExplanation" class="ai-interpretation__body">
      <InterpretationBlockView
        :block="moduleExplanation"
        :references="interpretation?.references"
        :print="print"
      />
    </div>

    <div v-else-if="isReview" class="ai-review-grid">
      <div v-if="content.priority_focus.length" class="ai-review-block">
        <h4>优先关注</h4>
        <InterpretationBlockView
          v-for="item in content.priority_focus"
          :key="item.text"
          :block="item"
          :references="interpretation?.references"
          :print="print"
        />
      </div>
      <div v-if="content.training_suggestions.length" class="ai-review-block">
        <h4>条件式训练建议</h4>
        <article v-for="item in content.training_suggestions" :key="item.title">
          <strong>{{ item.title }}</strong>
          <InterpretationBlockView :block="item" :references="interpretation?.references" :print="print" />
          <dl class="ai-suggestion-details">
            <template v-if="item.goal"><dt>目标</dt><dd>{{ item.goal }}</dd></template>
            <template v-if="item.drill"><dt>练习</dt><dd>{{ item.drill }}</dd></template>
            <template v-if="item.dose_or_condition"><dt>执行条件</dt><dd>{{ item.dose_or_condition }}</dd></template>
            <template v-if="item.stop_conditions?.length"><dt>停止条件</dt><dd>{{ item.stop_conditions.join('；') }}</dd></template>
            <template v-if="item.success_criterion"><dt>复测标准</dt><dd>{{ item.success_criterion }}</dd></template>
          </dl>
          <small>{{ item.applicability }}</small>
          <ul v-if="item.cautions?.length" class="ai-cautions">
            <li v-for="caution in item.cautions" :key="caution">{{ caution }}</li>
          </ul>
        </article>
      </div>
      <div v-if="content.retest_targets.length" class="ai-review-block">
        <h4>复测目标</h4>
        <div v-for="item in content.retest_targets" :key="item.metric_key">
          <strong>{{ item.metric_key }}</strong>
          <InterpretationBlockView :block="item" :references="interpretation?.references" :print="print" />
          <small v-if="item.success_criterion">复测标准：{{ item.success_criterion }}</small>
        </div>
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

.ai-suggestion-details { display: grid; grid-template-columns: auto 1fr; gap: 4px 8px; margin: 8px 0; color: #435363; font-size: 12px; line-height: 1.5; }
.ai-suggestion-details dt { color: #6d7a86; }
.ai-suggestion-details dd { margin: 0; }
.ai-cautions { margin: 8px 0; padding-left: 18px; color: #8a6116; font-size: 12px; line-height: 1.5; }

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

</style>
