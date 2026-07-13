<script setup lang="ts">
import type { NormalizedSection } from '../../../types/report'
import MetricCard from '../shared/MetricCard.vue'
import FindingList from '../shared/FindingList.vue'
import RecommendationList from '../shared/RecommendationList.vue'
import EvidenceFrameCard from '../shared/EvidenceFrameCard.vue'
import ReportChart from '../shared/ReportChart.vue'

defineProps<{
  section: NormalizedSection
}>()
</script>

<template>
  <section class="report-section generic-section">
    <header class="section-header">
      <h2>{{ section.title }}</h2>
      <p v-if="section.summary" class="section-summary">{{ section.summary }}</p>
    </header>

    <div v-if="section.metrics?.length" class="simple-metric-row">
      <div v-for="metric in section.metrics" :key="metric.key" class="simple-metric">
        <span class="simple-metric__label">{{ metric.label }}</span>
        <strong class="simple-metric__value">{{ metric.value }}{{ metric.unit ?? '' }}</strong>
      </div>
    </div>

    <div v-if="section.assets?.length" class="simple-frame-grid">
      <EvidenceFrameCard
        v-for="asset in section.assets"
        :key="asset.key"
        :asset="asset"
      />
    </div>

    <div v-if="section.charts?.length" class="simple-chart-grid">
      <ReportChart
        v-for="chart in section.charts"
        :key="chart.key"
        :chart="chart"
      />
    </div>

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
  </section>
</template>

<style scoped>
.generic-section {
  background: #ffffff;
  border: 1px solid #e6edf3;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 20px;
}

.section-header {
  margin-bottom: 16px;
}

.section-header h2 {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
}

.section-summary {
  margin-top: 8px;
  color: #5f6b7a;
}

.simple-metric-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 16px;
}

.simple-metric {
  padding: 12px 16px;
  background: #f7f9fb;
  border-radius: 10px;
  min-width: 140px;
}

.simple-metric__label {
  display: block;
  font-size: 13px;
  color: #5f6b7a;
  margin-bottom: 4px;
}

.simple-metric__value {
  font-size: 18px;
}

.simple-frame-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.simple-chart-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
  margin-bottom: 20px;
}
</style>
