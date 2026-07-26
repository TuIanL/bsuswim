<template>
  <div>
    <section v-if="viewModel?.overview" class="report-identity">
      <div>
        <span class="report-identity__eyebrow">运动表现分析报告</span>
        <h1>{{ viewModel.overview.athlete?.name || '未命名运动员' }}</h1>
        <p>
          {{ viewModel.overview.session?.stroke_type === 'freestyle' ? '自由泳' : viewModel.overview.session?.stroke_type || '游泳训练' }}
          · {{ viewModel.overview.session?.distance_m ? `${viewModel.overview.session.distance_m} 米` : '距离未记录' }}
          · {{ viewModel.overview.session?.session_date || '日期未记录' }}
        </p>
      </div>
      <div class="report-identity__facts">
        <span>训练记录</span><strong>#{{ viewModel.overview.session?.id || props.sessionId }}</strong>
        <span>机位</span><strong>{{ viewModel.overview.video?.view_type === 'side' ? '侧面' : viewModel.overview.video?.view_type || '-' }}</strong>
      </div>
    </section>
    <div class="page-head">
      <div>
        <h1>HTML 报告</h1>
        <p>基于后端报告 API 展示。</p>
      </div>
      <div class="page-head-actions">
        <el-button
          v-if="pdfStatus === 'exported'"
          type="primary"
          :loading="pdfExporting"
          @click="downloadPdf"
        >
          下载 PDF
        </el-button>
        <el-button
          v-else-if="pdfStatus === 'exporting'"
          disabled
          loading
        >
          正在导出...
        </el-button>
        <el-button
          v-else-if="pdfStatus === 'export_failed'"
          type="danger"
          @click="exportPdf"
        >
          导出失败，重试
        </el-button>
        <el-button
          v-else
          @click="exportPdf"
        >
          {{ pdfStatus === 'stale' ? '报告已更新，重新导出 PDF' : '导出 PDF' }}
        </el-button>
      </div>
    </div>

    <div v-if="loading" class="section">加载中...</div>
    <el-empty v-else-if="errorMessage" class="section" :description="errorMessage">
      <el-button @click="$router.push('/tasks')">返回任务管理</el-button>
      <el-button type="primary" @click="load">刷新报告</el-button>
    </el-empty>

    <template v-else-if="viewModel">
      <ReportSummaryPanel
        v-if="viewModel.summary"
        :summary="viewModel.summary"
        :overview="viewModel.overview"
      />

      <section class="report-sections">
        <ReportSectionRenderer
          v-for="section in viewModel.sections"
          :key="section.key"
          :section="section"
          :video="viewModel.video"
        />
      </section>

      <section
        v-if="viewModel.provenance"
        class="section report-provenance"
      >
        <h2>报告来源</h2>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="来源">
            {{ (viewModel.provenance as any)?.source ?? '-' }}
          </el-descriptions-item>
          <el-descriptions-item
            v-if="(viewModel.provenance as any)?.generated_at"
            label="生成时间"
          >
            {{ (viewModel.provenance as any)?.generated_at }}
          </el-descriptions-item>
        </el-descriptions>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  downloadReportPdf,
  exportReportPdf,
  generateReport,
  getReport,
  getReportPdfStatus
} from '../services/api'
import { normalizeReportData } from '../utils/reportAdapter'
import type { NormalizedReportViewModel } from '../types/report'
import ReportSectionRenderer from '../components/report/ReportSectionRenderer.vue'
import ReportSummaryPanel from '../components/report/ReportSummaryPanel.vue'

const props = defineProps<{ sessionId: string }>()
const route = useRoute()

const loading = ref(true)
const errorMessage = ref('')
const viewModel = ref<NormalizedReportViewModel | null>(null)
const pdfStatus = ref<string>('not_exported')
const pdfExporting = ref(false)

const demoFormat = computed<'legacy' | 'swim_v1'>(() => {
  const value = route.query.demo_format
  return value === 'swim_v1' ? 'swim_v1' : 'legacy'
})

async function load() {
  loading.value = true
  errorMessage.value = ''
  viewModel.value = null
  try {
    const raw = await getReport(Number(props.sessionId), { demoFormat: demoFormat.value })
    viewModel.value = normalizeReportData(raw)
  } catch (error: any) {
    try {
      const raw = await generateReport(Number(props.sessionId))
      viewModel.value = normalizeReportData(raw)
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

  try {
    const status = await getReportPdfStatus(Number(props.sessionId))
    pdfStatus.value = status.pdf_status
  } catch {
    // status not critical
  }
}

async function exportPdf() {
  pdfExporting.value = true
  try {
    const result = await exportReportPdf(Number(props.sessionId))
    pdfStatus.value = result.pdf_status
    if (result.pdf_status === 'exported') {
      ElMessage.success('PDF 导出完成')
    }
  } catch (err: any) {
    pdfStatus.value = 'export_failed'
    ElMessage.error(err?.response?.data?.detail || 'PDF 导出失败')
  } finally {
    pdfExporting.value = false
  }
}

async function downloadPdf() {
  pdfExporting.value = true
  try {
    const blob = await downloadReportPdf(Number(props.sessionId))
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `游泳技术报告_${props.sessionId}.pdf`
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail?.message || 'PDF 下载失败')
  } finally {
    pdfExporting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.report-sections {
  margin-top: 0;
}

.report-identity {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: end;
  padding: 22px 4px 18px;
}

.report-identity__eyebrow {
  color: #5f6b7a;
  font-size: 13px;
}

.report-identity h1 {
  margin: 5px 0 4px;
  color: #162235;
  font-size: 30px;
  line-height: 1.15;
}

.report-identity p {
  margin: 0;
  color: #5f6b7a;
  font-size: 14px;
}

.report-identity__facts {
  display: grid;
  grid-template-columns: auto auto;
  gap: 5px 12px;
  color: #7b8794;
  font-size: 12px;
  text-align: right;
}

.report-identity__facts strong {
  color: #263445;
  font-size: 14px;
}

@media (max-width: 640px) {
  .report-identity {
    align-items: start;
    flex-direction: column;
  }

  .report-identity__facts {
    text-align: left;
  }
}

.report-provenance {
  background: #ffffff;
  border: 1px solid #e6edf3;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 20px;
}

.report-provenance h2 {
  font-size: 18px;
  font-weight: 700;
  margin: 0 0 16px;
}
</style>
