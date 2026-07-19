<template>
  <div class="wf-page">
    <div class="page-head">
      <div>
        <h1>侧面二维运动学分析</h1>
        <p>{{ session?.title || '加载中…' }}</p>
      </div>
      <div class="action-row">
        <el-button @click="$router.push('/tasks')">任务管理</el-button>
        <el-button
          v-if="activeTask"
          type="primary"
          plain
          @click="$router.push(`/workspace/${activeTask.id}`)"
        >查看任务详情</el-button>
      </div>
    </div>

    <div v-if="loading" class="section">加载中…</div>
    <el-empty v-else-if="!session" class="section" description="未找到训练记录" />
    <template v-else>
      <KinematicsWorkflowStepper :phase="workflowPhase" />

      <div class="info-grid section">
        <div class="info-item"><span>运动员</span><strong>{{ athlete?.name || `#${session.athlete_id}` }}</strong></div>
        <div class="info-item"><span>泳姿</span><strong>{{ strokeLabel(session.stroke_type) }}</strong></div>
        <div class="info-item"><span>距离</span><strong>{{ session.distance_m ? `${session.distance_m}m` : '-' }}</strong></div>
        <div class="info-item"><span>状态</span><strong>{{ phaseLabel(workflowPhase) }}</strong></div>
      </div>

      <!-- 步骤 1：侧面视频 -->
      <div class="section card">
        <h3>① 侧面视频</h3>
        <SideVideoStep
          :video="sideVideo"
          :uploading="videoUploading"
          @upload="onUploadVideo"
          @replace="onReplaceVideo"
        />
      </div>

      <!-- 步骤 2-4：标注 / 质量 / 模块（未绑定侧面视频前阻断） -->
      <div v-if="hasSideVideo" class="section card">
        <h3>② CVAT 标注与质量</h3>
        <CvatAnnotationStep
          :annotations="annotations"
          :selected-id="selectedAnnotationId"
          :ingesting="ingesting"
          :parse-error="parseError"
          :reparsing-id="reparsingId"
          @file="onAnnotationFile"
          @select="onSelectAnnotation"
          @reparse="onReparse"
          @replace="onReplaceAnnotation"
        />
        <template v-if="selectedAnnotation?.quality">
          <h4>标注质量</h4>
          <AnnotationQualityPanel :quality="selectedAnnotation.quality" />
          <h4>四类运动学模块可用性</h4>
          <KinematicsModuleReadinessGrid :readiness="selectedAnnotation.kinematics_module_readiness" />
        </template>
      </div>
      <div v-else class="section card muted-text">
        请先绑定侧面视频，再进行 CVAT 标注与质量确认。
      </div>

      <!-- 步骤 5：分析 -->
      <div class="section card">
        <h3>③ 生成二维运动学报告</h3>
        <el-button
          type="primary"
          :loading="submitting"
          :disabled="!canSubmit"
          @click="onSubmit"
        >生成二维运动学报告</el-button>
        <span v-if="!canSubmit && !activeTask && !completedTask" class="muted-text">
          需先绑定侧面视频并选择有效解析标注。
        </span>

        <AnalysisProgressPanel
          v-if="latestTask"
          class="mt"
          :progress="latestTask.pipeline_progress ?? null"
          :status="latestTask.status"
          :failed-stage="latestTask.failed_stage"
          :error-code="latestTask.error_code"
          :error-message="latestTask.error_message"
          :actions="latestTask.actions"
          :force-failed="workflowPhase === 'analysis_failed'"
          :busy="busy"
          @retry="onRetry"
          @resubmit="onResubmit"
        />
      </div>

      <!-- 步骤 6：报告 -->
      <div v-if="completedTask" class="section card">
        <h3>④ 报告</h3>
        <ReportReadyPanel
          :freshness="reportFreshness"
          :report-revision="reportTaskRevision"
          :selected-revision="selectedAnnotation?.normalized_revision ?? null"
          :pdf-status="pdfStatus"
          :pdf-url="pdfUrl"
          :pdf-busy="pdfBusy"
          @open-html="openReport"
          @export-pdf="exportPdf"
          @regenerate="onResubmit"
        />
      </div>

      <FutureCameraViewsPanel :videos="allVideos" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useKinematicsWorkflow } from '../../composables/useKinematicsWorkflow'
import { bindUploadedSessionVideo, uploadVideo, getReportPdfStatus, exportReportPdf, listSessionVideos } from '../../services/api'
import KinematicsWorkflowStepper from './KinematicsWorkflowStepper.vue'
import SideVideoStep from './SideVideoStep.vue'
import CvatAnnotationStep from './CvatAnnotationStep.vue'
import AnnotationQualityPanel from './AnnotationQualityPanel.vue'
import KinematicsModuleReadinessGrid from './KinematicsModuleReadinessGrid.vue'
import AnalysisProgressPanel from './AnalysisProgressPanel.vue'
import ReportReadyPanel from './ReportReadyPanel.vue'
import FutureCameraViewsPanel from './FutureCameraViewsPanel.vue'

const props = defineProps<{ sessionId: string }>()
const router = useRouter()
const sessionId = Number(props.sessionId)
const wf = useKinematicsWorkflow(sessionId)

const videoUploading = ref(false)
const ingesting = ref(false)
const parseError = ref<string | null>(null)
const reparsingId = ref<number | null>(null)
const busy = ref<'retry' | 'resubmit' | null>(null)
const pdfBusy = ref<'export' | null>(null)
const pdfStatus = ref<string>('not_exported')
const pdfUrl = ref<string | null>(null)
const allVideos = ref<any[]>([])

const {
  loading, session, athlete, sideVideo, annotations, latestTask, reportFreshness, hasSideVideo,
  selectedAnnotationId, selectedAnnotation, submitting, activeTask, completedTask, workflowPhase, canSubmit
} = wf

const reportTaskRevision = computed(() =>
  (latestTask.value?.request_payload as any)?.analysis_input?.annotation_revision ?? null
)

function strokeLabel(v: string) {
  return ({ freestyle: '自由泳', breaststroke: '蛙泳', backstroke: '仰泳', butterfly: '蝶泳', mixed: '混合' } as any)[v] || v
}
function phaseLabel(p: string) {
  return ({
    video_required: '待上传侧面视频', annotation_required: '待上传 CVAT 标注',
    annotation_processing: '标注解析中', annotation_review: '待确认标注质量',
    ready_to_analyze: '可提交分析', analysis_running: '分析进行中',
    analysis_failed: '分析失败', report_ready: '报告已生成'
  } as any)[p] || p
}

async function loadVideos() {
  try {
    allVideos.value = await listSessionVideos(sessionId)
  } catch { allVideos.value = [] }
}

async function onUploadVideo(file: File) {
  videoUploading.value = true
  try {
    const video = await uploadVideo(file)
    await bindUploadedSessionVideo(sessionId, video, { view_type: 'side', sync_offset_ms: 0 })
    await wf.refresh()
    await loadVideos()
    ElMessage.success('侧面视频已绑定')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '上传失败')
  } finally {
    videoUploading.value = false
  }
}

function onReplaceVideo() {
  ElMessageBox.confirm('替换侧面视频将解除当前绑定，是否继续？', '替换视频', {
    confirmButtonText: '继续', cancelButtonText: '取消', type: 'warning'
  }).then(() => {
    // 用户需在文件选择后上传；此处仅提示
    ElMessage.info('请选择新的侧面视频文件')
  })
}

async function onAnnotationFile(file: File) {
  ingesting.value = true
  parseError.value = null
  try {
    await wf.ingestCvat(file)
    ElMessage.success('CVAT 标注解析完成')
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    if (detail?.error?.annotation_file_id) {
      parseError.value = `${detail.error.message}（文件已保存，可重新解析）`
    } else {
      parseError.value = detail?.error?.message || detail || e?.message || '解析失败'
    }
  } finally {
    ingesting.value = false
  }
}

function onSelectAnnotation(id: number) {
  selectedAnnotationId.value = id
}

async function onReparse(id: number) {
  reparsingId.value = id
  try {
    await wf.reparse(id)
    ElMessage.success('重新解析完成')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '重新解析失败')
  } finally {
    reparsingId.value = null
  }
}

function onReplaceAnnotation() {
  ElMessage.info('请重新上传 CVAT 标注文件')
}

async function onSubmit() {
  let ack = false
  if (wf.requiresAck.value) {
    try {
      await ElMessageBox.confirm('部分标注数据质量不足，分析结果可能受限。是否继续？', '数据质量警告', {
        confirmButtonText: '仍然继续', cancelButtonText: '返回检查', type: 'warning'
      })
      ack = true
    } catch { return }
  }
  try {
    await wf.submit(ack)
    ElMessage.success('分析任务已提交，正在页面内跟踪进度')
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    if (detail?.error?.code === 'ANALYSIS_TASK_ALREADY_ACTIVE') {
      ElMessage.warning('已有分析任务进行中，已切换到该任务进度')
      await wf.refresh()
    } else if (detail?.code === 'ANNOTATION_QUALITY_BLOCKED') {
      ElMessageBox.alert(
        detail.details?.issues?.map((i: any) => i.user_message).join('\n') || '标注质量不足',
        '无法开始分析', { type: 'error' }
      )
    } else {
      ElMessage.error(detail?.error?.message || detail?.message || e?.message || '提交失败')
    }
  }
}

async function onRetry() {
  busy.value = 'retry'
  try { await wf.retry(); ElMessage.success('已重试') }
  catch (e: any) { ElMessage.error(e?.response?.data?.detail || e?.message || '重试失败') }
  finally { busy.value = null }
}

async function onResubmit() {
  busy.value = 'resubmit'
  try { await wf.resubmit(); ElMessage.success('已用当前标注重新生成') }
  catch (e: any) { ElMessage.error(e?.response?.data?.detail || e?.message || '重新生成失败') }
  finally { busy.value = null }
}

function openReport() {
  router.push(`/reports/${sessionId}`)
}

async function refreshPdf() {
  try {
    const s = await getReportPdfStatus(sessionId)
    pdfStatus.value = s.pdf_status
    pdfUrl.value = s.pdf_status === 'exported' ? `/api/v1/sessions/${sessionId}/report/pdf` : null
  } catch { pdfStatus.value = 'not_exported' }
}

async function exportPdf() {
  pdfBusy.value = 'export'
  try {
    const r = await exportReportPdf(sessionId, true)
    pdfStatus.value = r.pdf_status
    pdfUrl.value = r.pdf_url ?? pdfUrl.value
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || 'PDF 导出失败')
  } finally {
    pdfBusy.value = null
  }
}

onMounted(async () => {
  await wf.init()
  await loadVideos()
  await refreshPdf()
})
</script>

<style scoped>
.page-head { display: flex; align-items: center; justify-content: space-between; }
.action-row { display: flex; gap: 8px; }
.section { margin-bottom: 16px; }
.card { border: 1px solid #ebeef5; border-radius: 10px; padding: 16px; }
.card h3 { margin: 0 0 12px; }
.card h4 { margin: 16px 0 8px; }
.info-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.info-item { display: flex; flex-direction: column; }
.info-item span { font-size: 12px; color: #909399; }
.muted-text { color: #909399; font-size: 13px; margin-left: 8px; }
.mt { margin-top: 16px; }
</style>
