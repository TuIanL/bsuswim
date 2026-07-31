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
          v-if="viewModel?.aiInterpretation?.can_regenerate"
          :icon="Refresh"
          :loading="interpretationGenerating"
          @click="regenerateInterpretation"
        >
          重新生成 AI 解读
        </el-button>
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
      <AIInterpretationPanel
        :interpretation="viewModel.aiInterpretation"
        module-key="analysis_overview"
      />

      <section class="report-sections">
        <template v-for="section in viewModel.sections" :key="section.key">
          <ReportSectionRenderer :section="section" :video="viewModel.video" />
          <AIInterpretationPanel
            :interpretation="viewModel.aiInterpretation"
            :module-key="section.module_key || section.page_type || ''"
          />
        </template>
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

    <el-dialog
      v-model="interpretationDialogVisible"
      class="interpretation-progress-dialog"
      width="440px"
      :close-on-click-modal="false"
      :show-close="!interpretationGenerating"
    >
      <template #header>
        <div class="interpretation-progress-dialog__title">
          <span>AI 解读生成</span>
          <small>{{ interpretationElapsedText }}</small>
        </div>
      </template>
      <div class="interpretation-progress-dialog__body">
        <el-progress :percentage="interpretationPercentage" :show-text="false" :stroke-width="8" />
        <ol class="interpretation-progress-steps">
          <li :class="{ done: interpretationStage !== 'pending' }">
            <span>1</span><div><strong>准备报告事实</strong><small>已固定本次指标、发现与数据边界</small></div>
          </li>
          <li :class="{ active: interpretationStage === 'generating', done: interpretationStage === 'ready' }">
            <span>2</span><div><strong>{{ interpretationStage === 'generating' ? '模型正在生成解读' : '等待模型响应' }}</strong><small>Qwen 请求仍在后台执行，可关闭本窗口后稍后查看报告</small></div>
          </li>
          <li :class="{ done: interpretationStage === 'ready' }">
            <span>3</span><div><strong>校验并保存结果</strong><small>核对事实引用、数值和安全边界</small></div>
          </li>
        </ol>
        <p v-if="interpretationStage === 'timed_out'" class="interpretation-progress-dialog__notice">
          生成耗时较长，任务仍在后台继续。稍后刷新报告即可读取结果。
        </p>
        <p v-else-if="interpretationStage === 'failed'" class="interpretation-progress-dialog__notice is-error">
          {{ interpretationErrorMessage || viewModel?.aiInterpretation?.error?.message || 'AI 解读生成失败' }}
        </p>
      </div>
      <template #footer>
        <el-button @click="interpretationDialogVisible = false">
          {{ interpretationGenerating ? '后台继续生成' : '关闭' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import {
  downloadReportPdf,
  exportReportPdf,
  generateReport,
  getReport,
  getReportInterpretation,
  generateReportInterpretation,
  getReportPdfStatus
} from '../services/api'
import { normalizeReportData } from '../utils/reportAdapter'
import type { NormalizedReportViewModel } from '../types/report'
import ReportSectionRenderer from '../components/report/ReportSectionRenderer.vue'
import ReportSummaryPanel from '../components/report/ReportSummaryPanel.vue'
import AIInterpretationPanel from '../components/report/AIInterpretationPanel.vue'

const props = defineProps<{ sessionId: string }>()
const route = useRoute()

const loading = ref(true)
const errorMessage = ref('')
const viewModel = ref<NormalizedReportViewModel | null>(null)
const pdfStatus = ref<string>('not_exported')
const pdfExporting = ref(false)
const interpretationGenerating = ref(false)
const interpretationDialogVisible = ref(false)
const interpretationStartedAt = ref<number | null>(null)
const interpretationElapsedSeconds = ref(0)
const interpretationTimedOut = ref(false)
const interpretationErrorMessage = ref('')
let interpretationClock: number | undefined

const interpretationStatus = computed(() => viewModel.value?.aiInterpretation?.status || 'pending')
const interpretationStage = computed(() => {
  if (interpretationErrorMessage.value) return 'failed'
  if (interpretationTimedOut.value && ['pending', 'generating'].includes(interpretationStatus.value)) return 'timed_out'
  if (interpretationStatus.value === 'ready') return 'ready'
  if (interpretationStatus.value === 'failed') return 'failed'
  if (interpretationStatus.value === 'generating') return 'generating'
  return 'pending'
})
const interpretationPercentage = computed(() => {
  if (interpretationStage.value === 'ready') return 100
  if (interpretationStage.value === 'failed') return 100
  if (interpretationStage.value === 'timed_out') return 92
  if (interpretationStage.value === 'generating') return Math.min(82, 32 + Math.floor(interpretationElapsedSeconds.value / 3))
  return 16
})
const interpretationElapsedText = computed(() => `${interpretationElapsedSeconds.value} 秒`)

function startInterpretationClock() {
  interpretationStartedAt.value = Date.now()
  interpretationElapsedSeconds.value = 0
  interpretationTimedOut.value = false
  interpretationErrorMessage.value = ''
  window.clearInterval(interpretationClock)
  interpretationClock = window.setInterval(() => {
    if (interpretationStartedAt.value) {
      interpretationElapsedSeconds.value = Math.floor((Date.now() - interpretationStartedAt.value) / 1000)
    }
  }, 1000)
}

function stopInterpretationClock() {
  window.clearInterval(interpretationClock)
  interpretationClock = undefined
}

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

async function pollInterpretation() {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    const interpretation = await getReportInterpretation(Number(props.sessionId))
    if (viewModel.value) viewModel.value.aiInterpretation = interpretation
    if (!['pending', 'generating'].includes(interpretation.status)) {
      stopInterpretationClock()
      return
    }
    await new Promise((resolve) => window.setTimeout(resolve, 1500))
  }
  interpretationTimedOut.value = true
}

async function regenerateInterpretation() {
  interpretationGenerating.value = true
  interpretationErrorMessage.value = ''
  try {
    const result = await generateReportInterpretation(Number(props.sessionId), true)
    if (result.status === 'not_configured') {
      interpretationErrorMessage.value = 'AI 解读尚未配置'
      interpretationDialogVisible.value = true
      ElMessage.warning(interpretationErrorMessage.value)
      return
    }
    if (!result.interpretation_id || !['pending', 'generating'].includes(result.status)) {
      throw new Error('服务端未确认 AI 解读任务，未开始调用模型')
    }
    if (viewModel.value?.aiInterpretation) {
      viewModel.value.aiInterpretation.status = result.status as any
    }
    interpretationDialogVisible.value = true
    startInterpretationClock()
    await pollInterpretation()
    if (viewModel.value?.aiInterpretation?.status === 'ready') ElMessage.success('AI 解读已更新')
  } catch (error: any) {
    stopInterpretationClock()
    interpretationErrorMessage.value =
      error?.response?.data?.detail?.message || error?.message || 'AI 解读生成失败'
    interpretationDialogVisible.value = true
    ElMessage.error(interpretationErrorMessage.value)
  } finally {
    interpretationGenerating.value = false
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

onMounted(async () => {
  await load()
  if (['pending', 'generating'].includes(viewModel.value?.aiInterpretation?.status || '')) {
    void pollInterpretation()
  }
})

onBeforeUnmount(() => stopInterpretationClock())
</script>

<style scoped>
.report-sections {
  margin-top: 0;
}

.interpretation-progress-dialog__title { display: flex; justify-content: space-between; align-items: baseline; color: #1f2d3d; }
.interpretation-progress-dialog__title small { color: #718096; font-size: 12px; font-variant-numeric: tabular-nums; }
.interpretation-progress-dialog__body { padding-top: 2px; }
.interpretation-progress-steps { margin: 20px 0 6px; padding: 0; list-style: none; display: grid; gap: 14px; }
.interpretation-progress-steps li { display: grid; grid-template-columns: 26px 1fr; gap: 10px; color: #94a3b0; }
.interpretation-progress-steps li > span { width: 24px; height: 24px; display: grid; place-items: center; border: 1px solid #d8e0e6; border-radius: 50%; font-size: 12px; }
.interpretation-progress-steps li strong { display: block; color: inherit; font-size: 13px; }
.interpretation-progress-steps li small { display: block; margin-top: 3px; color: #8a98a7; font-size: 12px; line-height: 1.45; }
.interpretation-progress-steps li.active { color: #247cdb; }
.interpretation-progress-steps li.active > span { border-color: #247cdb; background: #247cdb; color: #fff; }
.interpretation-progress-steps li.done { color: #27854a; }
.interpretation-progress-steps li.done > span { border-color: #bde4c8; background: #eef9f1; }
.interpretation-progress-dialog__notice { margin: 18px 0 0; padding: 9px 10px; background: #fff8e7; color: #8a6116; font-size: 12px; line-height: 1.5; }
.interpretation-progress-dialog__notice.is-error { background: #fff1f1; color: #b84444; }

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
