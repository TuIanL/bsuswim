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
import { ElMessage } from 'element-plus'
import { bindUploadedSessionVideo, getAthlete, getSession, listSessionVideos, submitAnalysis as submitBackendAnalysis, uploadVideo } from '../services/api'
import type { Athlete, BackendSessionVideoView, SessionVideoView, TrainingSession, UploadStatus } from '../types'

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
}

const props = defineProps<{ sessionId: string }>()
const router = useRouter()
const loading = ref(true)
const submitting = ref(false)
const session = ref<TrainingSession | null>(null)
const athlete = ref<Athlete | null>(null)
const cameras = reactive<CameraState[]>([
  { view: 'side', backendView: 'side', label: '侧面机位', description: '观察身体水平度、划水路径', file: null, fileName: '', fileSize: 0, status: 'pending', syncOffsetMs: 0, fps: 60, resolution: '1920x1080' },
  { view: 'front', backendView: 'front', label: '正面机位', description: '观察身体中线与左右对称', file: null, fileName: '', fileSize: 0, status: 'pending', syncOffsetMs: 0, fps: 60, resolution: '1920x1080' },
  { view: 'top', backendView: 'top', label: '俯视机位', description: '观察路线偏移与入水角度', file: null, fileName: '', fileSize: 0, status: 'pending', syncOffsetMs: 0, fps: 60, resolution: '1920x1080' },
  { view: 'underwater', backendView: 'underwater', label: '水下机位', description: '观察抱水、推水和打腿', file: null, fileName: '', fileSize: 0, status: 'pending', syncOffsetMs: 0, fps: 60, resolution: '1920x1080' },
  { view: 'semi_underwater', backendView: 'other', label: '半水下机位', description: '预留水面交界视角', file: null, fileName: '', fileSize: 0, status: 'pending', syncOffsetMs: 0, fps: 60, resolution: '1920x1080' }
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
        }
      })
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
    ElMessage.success(`${camera.label}已绑定`)
  } catch (error: any) {
    camera.status = 'failed'
    ElMessage.error(error?.response?.data?.detail || error?.message || '上传失败')
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
  submitting.value = true
  try {
    const task = await submitBackendAnalysis(session.value.id)
    ElMessage.success('分析任务已提交')
    router.push(`/workspace/${task.id}`)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '提交分析失败')
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

onMounted(load)
</script>
