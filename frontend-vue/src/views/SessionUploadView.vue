<template>
  <div>
    <div class="page-head">
      <div>
        <h1>多机位视频上传</h1>
        <p>{{ session?.title || '加载测试任务' }}</p>
      </div>
      <div class="action-row">
        <el-button @click="$router.push('/tasks')">任务管理</el-button>
        <el-button type="primary" :loading="submitting" :disabled="!hasSuccessVideo" @click="submitAnalysis">提交分析</el-button>
      </div>
    </div>

    <div v-if="loading" class="section">加载中...</div>
    <el-empty v-else-if="!session" class="section" description="未找到测试任务" />
    <template v-else>
      <div class="section">
        <div class="info-grid">
          <div class="info-item"><span>运动员</span><strong>{{ athlete?.name || `#${session.athlete_id}` }}</strong></div>
          <div class="info-item"><span>测试日期</span><strong>{{ session.session_date || '-' }}</strong></div>
          <div class="info-item"><span>泳姿</span><strong>{{ strokeLabel(session.stroke_type) }}</strong></div>
          <div class="info-item"><span>距离</span><strong>{{ session.distance_m ? `${session.distance_m}m` : '-' }}</strong></div>
          <div class="info-item"><span>泳池长度</span><strong>{{ session.pool_length_m ? `${session.pool_length_m}m` : '-' }}</strong></div>
          <div class="info-item"><span>状态</span><strong>{{ statusLabel(session.status) }}</strong></div>
        </div>
      </div>

      <div class="camera-grid">
        <div v-for="camera in cameras" :key="camera.view" class="camera-card">
          <div class="camera-card-head">
            <div>
              <h3>{{ camera.label }}</h3>
              <span class="muted-text">{{ camera.description }}</span>
            </div>
            <el-tag :type="tagType(camera.status)">{{ statusText(camera.status) }}</el-tag>
          </div>

          <el-upload
            drag
            :auto-upload="false"
            :limit="1"
            accept="video/*"
            :show-file-list="false"
            :on-change="makeFileHandler(camera.view)"
          >
            <div>{{ camera.fileName || '拖入视频或点击选择' }}</div>
            <small>{{ camera.fileSize ? formatSize(camera.fileSize) : '支持浏览器可识别的视频格式' }}</small>
          </el-upload>

          <el-form class="auth-form" label-position="top">
            <el-form-item label="同步偏移 ms">
              <el-input-number v-model="camera.syncOffsetMs" class="full-select" :step="20" />
            </el-form-item>
            <el-form-item label="FPS">
              <el-input-number v-model="camera.fps" class="full-select" :min="1" :max="240" />
            </el-form-item>
            <el-form-item label="分辨率">
              <el-input v-model="camera.resolution" placeholder="1920x1080" />
            </el-form-item>
          </el-form>

          <el-button
            class="full-button"
            type="primary"
            plain
            :loading="camera.status === 'uploading'"
            :disabled="!camera.file"
            @click="uploadCamera(camera.view)"
          >
            {{ camera.status === 'failed' ? '重试上传' : '上传并绑定' }}
          </el-button>

          <!-- 标注文件区域：仅视频已绑定后显示 -->
          <div v-if="camera.status === 'success' && camera.sessionVideoId" class="annotation-section">
            <el-divider />
            <h4>标注文件</h4>

            <div v-if="camera.annotations.length" class="annotation-list">
              <div v-for="ann in camera.annotations" :key="ann.id" class="annotation-item">
                <div class="annotation-info">
                  <span class="ann-filename">{{ ann.original_filename }}</span>
                  <span class="ann-meta">
                    {{ sourceLabel(ann.source) }} · v{{ ann.version }}
                  </span>
                </div>
                <div class="annotation-actions">
                  <el-tag :type="ann.status === 'uploaded' ? 'info' : ann.status === 'parsed' ? 'success' : ann.status === 'archived' ? 'warning' : 'danger'" size="small">
                    {{ annotationStatusLabel(ann.status) }}
                  </el-tag>
                  <el-tag v-if="ann.quality_status" :type="qualityTagType(ann.quality_status)" size="small" effect="plain">
                    {{ qualityLabel(ann.quality_status) }}
                  </el-tag>
                  <el-button size="small" text @click="downloadAnnotation(ann.id)">下载</el-button>
                  <el-button v-if="ann.status !== 'archived'" size="small" text type="warning" @click="archiveAnnotationFile(ann.id, camera.view)">归档</el-button>
                </div>
              </div>
            </div>
            <el-empty v-else description="暂无标注文件" :image-size="40" />

            <div class="annotation-upload-row">
              <el-select v-model="camera.annotationSource" size="small" class="source-select">
                <el-option label="Kinovea" value="kinovea" />
                <el-option label="Dartfish" value="dartfish" />
                <el-option label="Manual JSON" value="manual_json" />
                <el-option label="AI Pose" value="ai_pose" />
                <el-option label="CVAT Skeleton XML" value="cvat" />
              </el-select>
              <el-input-number
                v-model="camera.annotationFps"
                size="small"
                :min="1"
                :max="240"
                placeholder="FPS"
                class="fps-input"
              />
              <el-upload
                :auto-upload="false"
                :limit="1"
                :show-file-list="false"
                accept=".csv,.json,.xml,.txt,.kva"
                :on-change="makeAnnotationFileHandler(camera.view)"
              >
                <el-button size="small" type="primary" plain :loading="camera.annotationStage === 'ingesting'" :disabled="!camera.annotationFile">
                  {{ camera.annotationFileName || '选择标注文件' }}
                </el-button>
              </el-upload>
              <el-button
                size="small"
                type="primary"
                :loading="camera.annotationStage === 'ingesting'"
                :disabled="!camera.annotationFile"
                @click="uploadAnnotationFile(camera.view)"
              >
                上传并处理标注
              </el-button>
            </div>

            <!-- 标注处理状态 -->
            <div v-if="camera.annotationStage === 'ingesting'" class="annotation-stage-info">
              <el-icon class="is-loading"><svg viewBox="0 0 1024 1024"><path d="M512 1024C229.376 1024 0 794.624 0 512S229.376 0 512 0s512 229.376 512 512-229.376 512-512 512z m0-938.667C276.48 85.333 85.333 276.48 85.333 512S276.48 938.667 512 938.667 938.667 747.52 938.667 512 747.52 85.333 512 85.333z"/></svg></el-icon>
              <span>正在上传并处理标注…</span>
            </div>
            <div v-else-if="camera.annotationStage === 'failed'" class="annotation-stage-info stage-failed">
              <span>处理失败，请重试</span>
            </div>

            <!-- 已解析标注的选择 -->
            <div v-if="camera.annotations.filter(a => a.status === 'parsed').length > 0" class="annotation-selection">
              <h4>选择分析标注</h4>
              <el-radio-group v-model="camera.selectedAnnotationId" class="annotation-radio-group">
                <div v-for="ann in camera.annotations.filter(a => a.status === 'parsed')" :key="ann.id" class="annotation-radio-item">
                  <el-radio
                    :value="ann.normalized_annotation_id"
                    :disabled="ann.quality_status === 'invalid'"
                  >
                    <span class="ann-filename">{{ ann.original_filename }}</span>
                    <span class="ann-meta">
                      {{ sourceLabel(ann.source) }} · v{{ ann.version }}
                      <el-tag v-if="ann.quality_status" :type="qualityTagType(ann.quality_status)" size="small" effect="plain">
                        {{ qualityLabel(ann.quality_status) }}
                      </el-tag>
                      <span v-if="ann.normalized_revision" class="revision-badge">rev{{ ann.normalized_revision }}</span>
                    </span>
                  </el-radio>
                </div>
              </el-radio-group>
            </div>
          </div>
        </div>
      </div>

      <div class="section">
        <div class="action-row">
          <el-button @click="saveDraft">保存草稿</el-button>
          <el-button type="primary" :loading="submitting" :disabled="!hasSuccessVideo" @click="submitAnalysis">提交分析</el-button>
          <span class="muted-text">至少成功绑定一个机位视频后可提交分析。</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { UploadFile } from 'element-plus'
import { ElMessage, ElMessageBox } from 'element-plus'
import { archiveAnnotation, bindUploadedSessionVideo, downloadAnnotationUrl, getAthlete, getAnnotationDetail, getSession, ingestAnnotation, listAnnotations, listSessionVideos, submitAnalysis as submitBackendAnalysis, uploadVideo } from '../services/api'
import type { AnalysisReadiness, AnnotationFileListItem, AnnotationIngestResponse, AnnotationWorkflowStage, Athlete, BackendSessionVideoView, QualityStatus, SessionVideoView, TrainingSession, UploadStatus } from '../types'

type CameraState = {
  view: SessionVideoView
  backendView: BackendSessionVideoView
  label: string
  description: string
  file: File | null
  fileName: string
  fileSize: number
  status: UploadStatus
  syncOffsetMs: number
  fps?: number
  resolution: string
  sessionVideoId: number | null
  videoFileId: number | null
  annotations: AnnotationFileListItem[]
  annotationFile: File | null
  annotationFileName: string
  annotationSource: string
  annotationFps: number | undefined
  annotationStage: AnnotationWorkflowStage
  selectedAnnotationId: number | null
}

const props = defineProps<{ sessionId: string }>()
const router = useRouter()
const loading = ref(true)
const submitting = ref(false)
const session = ref<TrainingSession | null>(null)
const athlete = ref<Athlete | null>(null)
function makeCamera(view: SessionVideoView, backendView: BackendSessionVideoView, label: string, description: string): CameraState {
  return {
    view, backendView, label, description,
    file: null, fileName: '', fileSize: 0, status: 'pending' as UploadStatus,
    syncOffsetMs: 0, fps: 60, resolution: '1920x1080',
    sessionVideoId: null, videoFileId: null,
    annotations: [],
    annotationFile: null, annotationFileName: '', annotationSource: 'kinovea', annotationFps: 60,
    annotationStage: 'idle', selectedAnnotationId: null,
  }
}

const cameras = reactive<CameraState[]>([
  makeCamera('side', 'side', '侧面机位', '观察身体水平度、划水路径'),
  makeCamera('front', 'front', '正面机位', '观察身体中线与左右对称'),
  makeCamera('top', 'top', '俯视机位', '观察路线偏移与入水角度'),
  makeCamera('underwater', 'underwater', '水下机位', '观察抱水、推水和打腿'),
  makeCamera('semi_underwater', 'other', '半水下机位', '预留水面交界视角')
])

const hasSuccessVideo = computed(() => cameras.some((item) => item.status === 'success'))

async function load() {
  loading.value = true
  const sessionId = Number(props.sessionId)
  try {
    session.value = await getSession(sessionId)
    if (session.value) {
      athlete.value = await getAthlete(session.value.athlete_id)
      const videos = await listSessionVideos(sessionId)
      videos.forEach((video) => {
        const camera = cameras.find((item) => item.backendView === video.view_type || item.view === video.view_type)
        if (camera) {
          camera.status = 'success'
          camera.fileName = video.video.original_filename
          camera.fileSize = video.video.size_bytes
          camera.syncOffsetMs = video.sync_offset_ms
          camera.fps = video.fps || camera.fps
          camera.resolution = video.resolution || camera.resolution
          camera.sessionVideoId = video.id
          camera.videoFileId = video.video_file_id
        }
      })
      // 加载已有标注
      for (const camera of cameras) {
        if (camera.status === 'success' && camera.videoFileId) {
          await loadAnnotations(camera.view)
        }
      }
    }
  } finally {
    loading.value = false
  }
}

function handleFile(view: SessionVideoView, file: UploadFile) {
  const camera = cameras.find((item) => item.view === view)
  if (!camera) return
  camera.file = file.raw || null
  camera.fileName = file.name
  camera.fileSize = file.size || 0
  camera.status = 'pending'
}

function makeFileHandler(view: SessionVideoView) {
  return (file: UploadFile) => handleFile(view, file)
}

async function uploadCamera(view: SessionVideoView) {
  const camera = cameras.find((item) => item.view === view)
  if (!camera?.file || !session.value) return
  camera.status = 'uploading'
  try {
    const video = await uploadVideo(camera.file)
    const link = await bindUploadedSessionVideo(session.value.id, video, {
      view_type: camera.backendView,
      fps: camera.fps,
      resolution: camera.resolution,
      sync_offset_ms: camera.syncOffsetMs
    })
    camera.status = 'success'
    camera.fileName = link.video.original_filename
    camera.fileSize = link.video.size_bytes
    camera.sessionVideoId = link.id
    camera.videoFileId = link.video_file_id
    ElMessage.success(`${camera.label}已绑定`)
    await loadAnnotations(view)
  } catch (error: any) {
    camera.status = 'failed'
    ElMessage.error(error?.response?.data?.detail || error?.message || '上传失败')
  }
}

async function loadAnnotations(view: SessionVideoView) {
  const camera = cameras.find((item) => item.view === view)
  if (!camera || !session.value || !camera.videoFileId) return
  try {
    const annotations = await listAnnotations(session.value.id, camera.videoFileId)
    camera.annotations = annotations

    const submittable = annotations
      .filter((a) => a.status === 'parsed' && a.quality_status !== 'invalid')
      .sort((a, b) => {
        const timeA = a.uploaded_at || ''
        const timeB = b.uploaded_at || ''
        return timeB.localeCompare(timeA) || b.id - a.id
      })
    camera.selectedAnnotationId = submittable.length > 0 ? submittable[0].normalized_annotation_id ?? null : null
  } catch {
    // 静默失败
  }
}

function makeAnnotationFileHandler(view: SessionVideoView) {
  return (file: UploadFile) => {
    const camera = cameras.find((item) => item.view === view)
    if (!camera) return
    camera.annotationFile = file.raw || null
    camera.annotationFileName = file.name
    if (file.name?.endsWith('.xml')) {
      camera.annotationSource = 'cvat'
    }
  }
}

async function uploadAnnotationFile(view: SessionVideoView) {
  const camera = cameras.find((item) => item.view === view)
  if (!camera?.annotationFile || !session.value || !camera.videoFileId) return
  camera.annotationStage = 'ingesting'
  try {
    const result = await ingestAnnotation(
      session.value.id,
      camera.videoFileId,
      camera.annotationFile,
      camera.annotationSource,
      camera.annotationFps || null,
    )
    camera.annotationFile = null
    camera.annotationFileName = ''
    camera.annotationStage = mapIngestQuality(result.quality?.status)
    if (camera.annotationStage === 'failed') {
      ElMessage.error('标注处理失败')
    } else {
      ElMessage.success('标注上传并处理完成')
    }
    await loadAnnotations(view)
  } catch (error: any) {
    camera.annotationStage = 'failed'
    const detail = error?.response?.data?.detail
    if (detail?.error?.code?.startsWith('ANNOTATION_INGEST')) {
      ElMessageBox.alert(
        `${detail.error.message}${detail.error.annotation_file_id ? '\n文件已保存，可重新解析。' : ''}`,
        '处理失败',
        { type: 'error', confirmButtonText: detail.error.annotation_file_id ? '知道了' : '关闭' }
      )
    } else {
      ElMessage.error(error?.response?.data?.detail || error?.message || '标注处理失败')
    }
  }
}

function mapIngestQuality(status: string | undefined): AnnotationWorkflowStage {
  if (status === 'valid') return 'ready'
  if (status === 'warning') return 'warning'
  if (status === 'invalid') return 'invalid'
  return 'failed'
}

function downloadAnnotation(annotationId: number) {
  window.open(downloadAnnotationUrl(annotationId), '_blank')
}

async function archiveAnnotationFile(annotationId: number, view: SessionVideoView) {
  try {
    await archiveAnnotation(annotationId)
    ElMessage.success('标注文件已归档')
    await loadAnnotations(view)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '归档失败')
  }
}

function saveDraft() {
  ElMessage.success('草稿已保存')
}

async function submitAnalysis() {
  if (!hasSuccessVideo.value) {
    ElMessage.warning('请至少绑定一个机位视频')
    return
  }
  if (!session.value) return

  const sideCamera = cameras.find((c) => c.view === 'side' && c.status === 'success')
  let annotationId: number | undefined
  let qualityStatus: QualityStatus | undefined
  let affectedModules: string[] = []
  if (sideCamera && sideCamera.selectedAnnotationId) {
    const selected = sideCamera.annotations.find(
      (a) => a.normalized_annotation_id === sideCamera.selectedAnnotationId
    )
    annotationId = selected?.normalized_annotation_id ?? undefined
    qualityStatus = selected?.quality_status
    affectedModules = selected?.analysis_readiness?.affected_modules || []
  }

  // invalid 直接阻断
  if (qualityStatus === 'invalid') {
    ElMessage.error('标注质量不足以开始分析，请检查后重试。')
    return
  }

  // warning 弹窗确认
  let acknowledge = false
  if (qualityStatus === 'warning') {
    try {
      const msg = affectedModules.length
        ? `以下模块将降级或不可用：${affectedModules.join('、')}`
        : '部分标注数据质量不足，分析结果可能受限。'
      await ElMessageBox.confirm(`${msg}是否继续？`, '数据质量警告', {
        confirmButtonText: '仍然继续',
        cancelButtonText: '返回检查',
        type: 'warning'
      })
      acknowledge = true
    } catch {
      return
    }
  }

  submitting.value = true
  try {
    const task = await submitBackendAnalysis(session.value.id, {
      normalized_annotation_id: annotationId,
      acknowledge_quality_warnings: acknowledge
    })
    ElMessage.success('分析任务已提交')
    router.push(`/workspace/${task.id}`)
  } catch (error: any) {
    const detail = error?.response?.data?.detail
    if (detail?.error?.code === 'ANNOTATION_QUALITY_BLOCKED') {
      ElMessageBox.alert(
        detail.error.details?.issues?.map((i: any) => i.user_message).join('\n') || '标注质量不足',
        '无法开始分析',
        { type: 'error' }
      )
    } else if (detail?.error?.code === 'ANNOTATION_SELECTION_REQUIRED') {
      ElMessageBox.alert('请选择一个标注文件后再提交分析。', '需要选择标注', { type: 'warning' })
    } else if (detail?.error?.code === 'ANNOTATION_INPUT_UNAVAILABLE') {
      ElMessageBox.alert('当前没有可用的标注，请检查标注文件状态。', '标注不可用', { type: 'warning' })
    } else {
      ElMessage.error(detail || error?.message || '提交分析失败')
    }
  } finally {
    submitting.value = false
  }
}

function formatSize(bytes: number) {
  if (!bytes) return '0 KB'
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function strokeLabel(value: string) {
  return { freestyle: '自由泳', breaststroke: '蛙泳', backstroke: '仰泳', butterfly: '蝶泳', mixed: '混合' }[value] || value
}

function statusLabel(value: string) {
  return { draft: '待上传', video_uploaded: '已上传', analyzing: '分析中', completed: '已完成', failed: '失败' }[value] || value
}

function statusText(value: UploadStatus) {
  return { pending: '待上传', uploading: '上传中', success: '已绑定', failed: '失败' }[value]
}

function tagType(value: UploadStatus) {
  return { pending: 'info', uploading: 'warning', success: 'success', failed: 'danger' }[value]
}

function sourceLabel(value: string) {
  return { kinovea: 'Kinovea', dartfish: 'Dartfish', manual_json: '手动 JSON', ai_pose: 'AI 姿态', unknown: '未知' }[value] || value
}

function annotationStatusLabel(value: string) {
  return { uploaded: '待解析', parsed: '已解析', parse_failed: '解析失败', archived: '已归档' }[value] || value
}

function qualityTagType(value: QualityStatus) {
  return { valid: 'success', warning: 'warning', invalid: 'danger' }[value] || 'info'
}

function qualityLabel(value: QualityStatus) {
  return { valid: '可分析', warning: '警告', invalid: '不可分析' }[value] || value
}

onMounted(load)
</script>

<style scoped>
.annotation-section {
  margin-top: 12px;
}
.annotation-stage-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  color: #909399;
  font-size: 13px;
}
.annotation-stage-info.stage-failed {
  color: #f56c6c;
}
.annotation-selection {
  margin-top: 12px;
}
.annotation-radio-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}
.annotation-radio-item {
  display: flex;
  align-items: center;
}
.annotation-radio-item .ann-filename {
  font-weight: 500;
  margin-right: 8px;
}
.annotation-radio-item .ann-meta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #909399;
  font-size: 12px;
}
.revision-badge {
  background: #ecf5ff;
  color: #409eff;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
}
</style>
