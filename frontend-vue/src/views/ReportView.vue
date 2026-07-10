<template>
  <div>
    <div class="page-head">
      <div>
        <h1>HTML 报告</h1>
        <p>基于后端报告 API 展示。</p>
      </div>
      <div class="page-head-actions">
        <el-button
          v-if="pdfStatus === 'exported'"
          type="primary"
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
      />

      <section class="report-sections">
        <ReportSectionRenderer
          v-for="section in viewModel.sections"
          :key="section.key"
          :section="section"
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
import { exportReportPdf, generateReport, getReport, getReportPdfStatus } from '../services/api'
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

function downloadPdf() {
  window.open(`/api/v1/sessions/${props.sessionId}/report/pdf`, '_blank')
}

onMounted(load)
</script>

<style scoped>
.report-sections {
  margin-top: 0;
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
