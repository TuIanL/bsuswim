<script setup lang="ts">
import type { ReportOverviewContext, ReportSummaryViewModel } from '../../types/report'
import ReportRadarChart from './shared/ReportRadarChart.vue'

const props = defineProps<{
  summary: ReportSummaryViewModel
  overview?: ReportOverviewContext
}>()

function formatOverviewList(value: unknown): string {
  if (!Array.isArray(value)) return value ? String(value) : '-'
  return value.map((item: any) => item?.label || item?.name || item?.module_key || String(item)).join('、') || '-'
}

function frameMappingText(annotation?: Record<string, unknown>): string {
  if (!annotation) return '-'
  const nested = annotation.frame_mapping as Record<string, unknown> | undefined
  const status = annotation.frame_mapping_status
  return status === 'verified' || nested?.verified === true ? '已确认' : '待确认'
}
</script>

<template>
  <section class="report-summary-panel">
    <div v-if="summary.overallScore !== undefined" class="score-block">
      <span class="score-label">综合评分</span>
      <strong class="score-value">{{ summary.overallScore }}</strong>
      <em class="score-max">/100</em>
    </div>

    <div v-if="props.overview" class="summary-block overview-block">
      <h3>数据与分析概况</h3>
      <div class="overview-grid">
        <div><span>视频文件</span><strong>{{ props.overview.video?.original_filename || '-' }}</strong></div>
        <div><span>视频规格</span><strong>{{ props.overview.video?.fps ? `${props.overview.video.fps} FPS` : '-' }}{{ props.overview.video?.resolution ? ` · ${props.overview.video.resolution}` : '' }}</strong></div>
        <div><span>标注帧数</span><strong>{{ props.overview.annotation?.frame_count ?? '-' }}</strong></div>
        <div><span>标注版本</span><strong>{{ props.overview.annotation?.revision ?? '-' }}</strong></div>
        <div><span>帧映射</span><strong>{{ frameMappingText(props.overview.annotation) }}</strong></div>
        <div><span>可用模块</span><strong>{{ formatOverviewList(props.overview.available_modules) }}</strong></div>
      </div>
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

.overview-block {
  padding: 14px 16px;
  background: #f7f9fb;
  border: 1px solid #e6edf3;
  border-radius: 10px;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px 18px;
}

.overview-grid div {
  display: grid;
  gap: 3px;
}

.overview-grid span {
  color: #7b8794;
  font-size: 12px;
}

.overview-grid strong {
  color: #263445;
  font-size: 14px;
  font-weight: 600;
  overflow-wrap: anywhere;
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
