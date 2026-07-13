<script setup lang="ts">
import { computed } from 'vue'
import type { NormalizedSection } from '../../types/report'
import { resolveSectionKind } from '../../utils/reportSections'

import ModuleSection from './sections/ModuleSection.vue'
import GenericSection from './sections/GenericSection.vue'

const props = defineProps<{
  section: NormalizedSection
}>()

const component = computed(() => {
  const kind = resolveSectionKind(props.section)

  switch (kind) {
    case 'module':
      return ModuleSection
    default:
      return GenericSection
  }
})
</script>

<template>
  <component :is="component" :section="section" />
</template>
