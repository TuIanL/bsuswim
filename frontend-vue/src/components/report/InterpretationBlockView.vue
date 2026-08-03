<script setup lang="ts">
import type { AIInterpretationBlock, AIReferenceCatalogItem } from '../../types'

const props = defineProps<{
  block: AIInterpretationBlock
  references?: AIReferenceCatalogItem[] | null
  print?: boolean
}>()

function refs(block: AIInterpretationBlock): AIReferenceCatalogItem[] {
  const typedRefs = [
    ...block.fact_refs.map((reference_id) => ({ reference_id, reference_type: 'fact' as const })),
    ...block.knowledge_refs.map((reference_id) => ({ reference_id, reference_type: 'knowledge' as const })),
    ...(block.evidence_refs || []).map((reference_id) => ({ reference_id, reference_type: 'evidence' as const })),
  ]
  const catalog = new Map((props.references || []).map((item) => [item.reference_id, item]))
  return typedRefs.map(({ reference_id, reference_type }) => catalog.get(reference_id) || {
    reference_id,
    reference_type,
    label: reference_id,
    target_available: false,
  })
}
</script>

<template>
  <div class="interpretation-block">
    <p v-if="block.observation"><strong>观测</strong>{{ block.observation }}</p>
    <p v-if="block.possible_explanations?.length"><strong>可能解释</strong>{{ block.possible_explanations.join('；') }}</p>
    <p v-if="block.potential_impact"><strong>潜在影响</strong>{{ block.potential_impact }}</p>
    <p v-if="block.action"><strong>建议</strong>{{ block.action }}</p>
    <p v-if="!block.observation && !block.possible_explanations?.length && !block.potential_impact && !block.action">
      {{ block.text }}
    </p>
    <div v-if="refs(block).length" class="ai-refs" :class="{ 'ai-refs--print': print }">
      <span class="ai-refs__label">依据</span>
      <template v-for="reference in refs(block)" :key="reference.reference_id">
        <a
          v-if="reference.target_available && reference.anchor"
          :href="`#${reference.anchor}`"
          class="ai-ref-link"
        >
          {{ reference.label }}
        </a>
        <span v-else class="ai-ref-link ai-ref-link--unavailable">{{ reference.label }}</span>
      </template>
    </div>
  </div>
</template>

<style scoped>
.interpretation-block p { margin: 6px 0; color: #435363; line-height: 1.6; }
.interpretation-block p strong { margin-right: 6px; color: #1f2d3d; }
.ai-refs { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-top: 10px; font-size: 11px; }
.ai-refs__label { color: #718096; }
.ai-ref-link { padding: 2px 6px; border: 1px solid #c9dfd8; border-radius: 4px; color: #167762; text-decoration: none; background: #f7fcfa; }
.ai-ref-link:hover { background: #e7f5f0; }
.ai-refs--print .ai-ref-link { padding: 0 3px; border: 0; background: transparent; }
</style>
