<script setup lang="ts">
import { computed } from 'vue'
import type { NormalizedSection, ReportVideoContext } from '../../../types/report'
import { resolveModuleLayout } from '../../../utils/reportSections'
import MetricOverview from '../shared/MetricOverview.vue'
import EvidenceFrameCard from '../shared/EvidenceFrameCard.vue'
import FindingList from '../shared/FindingList.vue'
import RecommendationList from '../shared/RecommendationList.vue'
import ReportChart from '../shared/ReportChart.vue'

const props = defineProps<{
  section: NormalizedSection
  video?: ReportVideoContext
}>()

const layout = computed(() => resolveModuleLayout(props.section))
const keyframeAssets = computed(() =>
  (props.section.assets ?? []).filter((asset) =>
    asset.artifact_type === 'annotated_keyframe' || asset.type === 'annotated_frame'
  )
)
const otherAssets = computed(() =>
  (props.section.assets ?? []).filter((asset) =>
    asset.artifact_type !== 'annotated_keyframe' && asset.type !== 'annotated_frame'
  )
)
</script>

<template>
  <section class="report-section module-section">
    <header class="section-header">
      <h2>{{ section.title }}</h2>
      <p v-if="section.summary" class="section-summary">{{ section.summary }}</p>
    </header>

    <MetricOverview v-if="section.metrics?.length" :metrics="section.metrics" />

    <div v-if="keyframeAssets.length" class="diagnostic-keyframes">
      <div class="diagnostic-keyframes__heading">自动诊断关键帧</div>
      <div class="frame-grid frame-grid--diagnostic">
        <EvidenceFrameCard
          v-for="asset in keyframeAssets"
          :key="asset.key"
          :asset="asset"
          :video="video"
        />
      </div>
    </div>

    <div v-if="section.quality_notes?.length" class="quality-notes">
      <div v-for="note in section.quality_notes" :key="note.code || note.message" class="quality-note">
        {{ note.message }}
      </div>
    </div>

    <div v-if="layout === 'frame_grid_3' && otherAssets.length" class="frame-grid frame-grid--3">
      <EvidenceFrameCard
        v-for="asset in otherAssets"
        :key="asset.key"
        :asset="asset"
        :video="video"
      />
    </div>

    <div v-else-if="layout === 'frame_grid_2' && otherAssets.length" class="frame-grid frame-grid--2">
      <EvidenceFrameCard
        v-for="asset in otherAssets"
        :key="asset.key"
        :asset="asset"
      />
    </div>

    <div v-else-if="layout === 'mixed_media' && otherAssets.length" class="mixed-media-layout">
      <div class="mixed-media-layout__assets">
        <EvidenceFrameCard
          v-for="asset in otherAssets"
          :key="asset.key"
          :asset="asset"
        />
      </div>
      <div class="mixed-media-layout__charts">
        <ReportChart
          v-for="chart in section.charts"
          :key="chart.key"
          :chart="chart"
        />
      </div>
    </div>

    <div v-else-if="layout === 'chart_grid'" class="chart-grid">
      <ReportChart
        v-for="chart in section.charts"
        :key="chart.key"
        :chart="chart"
      />
    </div>

    <div v-else class="module-compact">
      <div v-if="otherAssets.length" class="frame-grid frame-grid--auto">
        <EvidenceFrameCard
          v-for="asset in otherAssets"
          :key="asset.key"
          :asset="asset"
        />
      </div>
      <div v-if="section.charts?.length" class="chart-grid">
        <ReportChart
          v-for="chart in section.charts"
          :key="chart.key"
          :chart="chart"
        />
      </div>
    </div>

    <div class="module-text-grid">
      <FindingList
        v-if="section.findings?.length"
        title="关键发现"
        :items="section.findings"
      />
      <RecommendationList
        v-if="section.recommendations?.length"
        title="改进建议"
        :items="section.recommendations"
      />
    </div>
  </section>
</template>

<style scoped>
.module-section {
  background: #ffffff;
  border: 1px solid #e6edf3;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 20px;
}

.section-header {
  margin-bottom: 20px;
}

.section-header h2 {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
}

.section-summary {
  margin-top: 8px;
  color: #5f6b7a;
  font-size: 15px;
  line-height: 1.5;
}

.metric-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 20px;
}

.frame-grid {
  display: grid;
  gap: 16px;
  margin-bottom: 20px;
}

.frame-grid--3 {
  grid-template-columns: repeat(3, 1fr);
}

.frame-grid--2 {
  grid-template-columns: repeat(2, 1fr);
}

.frame-grid--auto {
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.diagnostic-keyframes {
  margin-bottom: 20px;
}

.diagnostic-keyframes__heading {
  margin-bottom: 10px;
  color: #203040;
  font-size: 14px;
  font-weight: 700;
}

.frame-grid--diagnostic {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.frame-grid--diagnostic :deep(.frame-image-wrap) {
  aspect-ratio: 16 / 9;
  min-height: 0;
}

.frame-grid--diagnostic :deep(.frame-image) {
  height: 100%;
  object-fit: cover;
}

.mixed-media-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.mixed-media-layout__assets {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

.mixed-media-layout__charts {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.module-compact {
  margin-bottom: 20px;
}

.module-text-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.quality-notes {
  display: grid;
  gap: 6px;
  margin: 0 0 16px;
}

.quality-note {
  padding: 8px 10px;
  border-left: 3px solid #e6a23c;
  background: #fdf6ec;
  color: #7a5b20;
  font-size: 12px;
}

@media (max-width: 900px) {
  .mixed-media-layout {
    grid-template-columns: 1fr;
  }

  .frame-grid--3 {
    grid-template-columns: 1fr;
  }

  .frame-grid--diagnostic {
    grid-template-columns: 1fr;
  }

  .frame-grid--2 {
    grid-template-columns: 1fr;
  }

  .module-text-grid {
    grid-template-columns: 1fr;
  }
}
</style>
