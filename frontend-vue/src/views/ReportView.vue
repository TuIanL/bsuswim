<template>
  <div>
    <div class="page-head">
      <div>
        <h1>HTML 报告</h1>
        <p>基于后端报告 API 展示，PDF 导出暂不可用。</p>
      </div>
      <el-button disabled>PDF 暂不可用</el-button>
    </div>

    <div v-if="loading" class="section">加载中...</div>
    <el-empty v-else-if="errorMessage" class="section" :description="errorMessage">
      <el-button @click="$router.push('/tasks')">返回任务管理</el-button>
      <el-button type="primary" @click="load">刷新报告</el-button>
    </el-empty>
    <div v-else-if="report" class="grid-two">
      <div class="section">
        <h2>{{ report.report.summary?.title }}</h2>
        <el-tag>{{ sourceLabel(report.source) }}</el-tag>
        <div class="metric-grid">
          <div class="metric">
            <span>综合评分</span>
            <strong>{{ report.report.summary?.overall_score }}</strong>
          </div>
          <div v-for="(value, key) in report.report.metrics || {}" :key="key" class="metric">
            <span>{{ key }}</span>
            <strong>{{ value }}</strong>
          </div>
        </div>
        <div ref="chartRef" style="height: 320px; margin-top: 20px" />
      </div>

      <div class="section">
        <h2>诊断与建议</h2>
        <el-timeline>
          <el-timeline-item v-for="item in report.report.diagnostics || []" :key="item.title" :timestamp="item.severity">
            <strong>{{ item.title }}</strong>
            <p>{{ item.evidence }}</p>
            <p>{{ item.suggestion }}</p>
          </el-timeline-item>
        </el-timeline>
        <h2>报告来源</h2>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="任务 ID">{{ report.task_id }}</el-descriptions-item>
          <el-descriptions-item label="训练记录 ID">{{ report.session_id }}</el-descriptions-item>
          <el-descriptions-item label="生成时间">{{ report.generated_at }}</el-descriptions-item>
          <el-descriptions-item label="来源">{{ report.source }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import * as echarts from 'echarts'
import { nextTick, onMounted, ref } from 'vue'
import { generateReport, getReport } from '../services/api'
import type { ReportData } from '../types'

const props = defineProps<{ sessionId: string }>()
const report = ref<ReportData | null>(null)
const loading = ref(true)
const errorMessage = ref('')
const chartRef = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

function renderChart() {
  if (!chartRef.value || !report.value) return
  chart?.dispose()
  chart = echarts.init(chartRef.value)
  const radar = report.value.report.charts?.radar || []
  chart.setOption({
    radar: {
      indicator: radar.map((item: any) => ({ name: item.name, max: 100 }))
    },
    series: [
      {
        type: 'radar',
        data: [{ value: radar.map((item: any) => item.value), name: '技术评分' }]
      }
    ]
  })
}

function sourceLabel(source: string) {
  if (source === 'demo') return 'Demo 数据'
  if (source.includes('mock')) return '模型服务 Mock 输出'
  return '模型服务输出'
}

async function load() {
  loading.value = true
  errorMessage.value = ''
  report.value = null
  try {
    report.value = await getReport(Number(props.sessionId))
  } catch (error: any) {
    try {
      report.value = await generateReport(Number(props.sessionId))
    } catch (generateError: any) {
      errorMessage.value =
        generateError?.response?.data?.detail ||
        error?.response?.data?.detail ||
        generateError?.message ||
        '报告尚未生成'
    }
  } finally {
    loading.value = false
  }
  await nextTick()
  renderChart()
}

onMounted(load)
</script>
