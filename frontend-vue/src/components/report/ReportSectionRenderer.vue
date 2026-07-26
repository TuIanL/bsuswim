<script setup lang="ts">
import { computed } from 'vue'
import type { NormalizedSection } from '../../types/report'
import { resolveSectionKind } from '../../utils/reportSections'

import ModuleSection from './sections/ModuleSection.vue'
import GenericSection from './sections/GenericSection.vue'
import KinematicsMetricsSection from './sections/KinematicsMetricsSection.vue'
import KinematicsArtifactsSection from './sections/KinematicsArtifactsSection.vue'
import type { ReportVideoContext } from '../../types/report'

const props = defineProps<{
  section: NormalizedSection
  video?: ReportVideoContext
}>()

const component = computed(() => {
  const kind = resolveSectionKind(props.section)

  switch (kind) {
    case 'module':
      return ModuleSection
    case 'kinematics_metrics':
      return KinematicsMetricsSection
    case 'kinematics_artifacts':
      return KinematicsArtifactsSection
    default:
      return GenericSection
  }
})
</script>

<template>
  <component :is="component" :section="section" :video="video" />
</template>
