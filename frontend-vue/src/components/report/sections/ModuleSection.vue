<script setup lang="ts">
import { computed } from 'vue'
import type { NormalizedSection } from '../../../types/report'
import { resolveModuleLayout } from '../../../utils/reportSections'
import MetricCard from '../shared/MetricCard.vue'
import EvidenceFrameCard from '../shared/EvidenceFrameCard.vue'
import FindingList from '../shared/FindingList.vue'
import RecommendationList from '../shared/RecommendationList.vue'
import ReportChart from '../shared/ReportChart.vue'

const props = defineProps<{
  section: NormalizedSection
}>()

const layout = computed(() => resolveModuleLayout(props.section))
</script>

<template>
  <section class="report-section module-section">
    <header class="section-header">
      <h2>{{ section.title }}</h2>
      <p v-if="section.summary" class="section-summary">{{ section.summary }}</p>
    </header>

    <div v-if="section.metrics?.length" class="metric-row">
      <MetricCard
        v-for="metric in section.metrics"
        :key="metric.key"
        :metric="metric"
      />
    </div>

    <div v-if="layout === 'frame_grid_3'" class="frame-grid frame-grid--3">
      <EvidenceFrameCard
        v-for="asset in section.assets"
        :key="asset.key"
        :asset="asset"
      />
    </div>

    <div v-else-if="layout === 'frame_grid_2'" class="frame-grid frame-grid--2">
      <EvidenceFrameCard
        v-for="asset in section.assets"
        :key="asset.key"
        :asset="asset"
      />
    </div>

    <div v-else-if="layout === 'mixed_media'" class="mixed-media-layout">
      <div class="mixed-media-layout__assets">
        <EvidenceFrameCard
          v-for="asset in section.assets"
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
      <div v-if="section.assets?.length" class="frame-grid frame-grid--auto">
        <EvidenceFrameCard
          v-for="asset in section.assets"
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

@media (max-width: 900px) {
  .mixed-media-layout {
    grid-template-columns: 1fr;
  }

  .frame-grid--3 {
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
