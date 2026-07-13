<script setup lang="ts">
import type { ReportSummaryViewModel } from '../../types/report'
import ReportRadarChart from './shared/ReportRadarChart.vue'

defineProps<{
  summary: ReportSummaryViewModel
}>()
</script>

<template>
  <section class="report-summary-panel">
    <div v-if="summary.overallScore !== undefined" class="score-block">
      <span class="score-label">综合评分</span>
      <strong class="score-value">{{ summary.overallScore }}</strong>
      <em class="score-max">/100</em>
    </div>

    <div v-if="summary.mainStrengths?.length" class="summary-block">
      <h3>主要优势</h3>
      <ul>
        <li v-for="item in summary.mainStrengths" :key="item">{{ item }}</li>
      </ul>
    </div>

    <div v-if="summary.mainLimitations?.length" class="summary-block">
      <h3>主要短板</h3>
      <ul>
        <li v-for="item in summary.mainLimitations" :key="item">{{ item }}</li>
      </ul>
    </div>

    <div v-if="summary.topFindings?.length" class="summary-block">
      <h3>关键发现</h3>
      <ul>
        <li v-for="item in summary.topFindings" :key="typeof item === 'string' ? item : (item as any).title">
          {{ typeof item === 'string' ? item : (item as any).title }}
        </li>
      </ul>
    </div>

    <div v-if="summary.radar?.length">
      <h3>技术能力画像</h3>
      <ReportRadarChart :data="summary.radar" />
    </div>
  </section>
</template>

<style scoped>
.report-summary-panel {
  background: #ffffff;
  border: 1px solid #e6edf3;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 20px;
}

.score-block {
  margin-bottom: 20px;
}

.score-label {
  font-size: 14px;
  color: #5f6b7a;
  display: block;
  margin-bottom: 4px;
}

.score-value {
  font-size: 36px;
  font-weight: 800;
  color: #1a2332;
}

.score-max {
  font-size: 16px;
  color: #a0aebf;
  font-style: normal;
}

.summary-block {
  margin-bottom: 16px;
}

.summary-block h3 {
  font-size: 15px;
  font-weight: 700;
  margin: 0 0 8px;
}

.summary-block ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.summary-block li {
  position: relative;
  padding-left: 16px;
  margin-bottom: 6px;
  font-size: 14px;
  color: #5f6b7a;
  line-height: 1.5;
}

.summary-block li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: #1a2332;
  font-weight: 700;
}
</style>
