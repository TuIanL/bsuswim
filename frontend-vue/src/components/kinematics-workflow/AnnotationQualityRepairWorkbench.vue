<template>
  <el-dialog
    :model-value="visible"
    title="修复标注质量"
    width="min(1040px, 96vw)"
    destroy-on-close
    @close="emit('close')"
  >
    <div class="repair-layout">
      <section class="video-panel">
        <div class="video-frame" :class="{ 'video-frame--error': videoError }">
          <video
            ref="videoRef"
            :src="videoUrl"
            controls
            preload="metadata"
            @loadedmetadata="onVideoMetadata"
            @timeupdate="onVideoTime"
            @error="videoError = true"
          />
          <canvas ref="canvasRef" @click="onCanvasClick" />
          <div v-if="videoError" class="video-error">视频无法加载，画布标注已禁用</div>
        </div>
        <div class="frame-controls">
          <el-button :disabled="!videoReady" @click="stepFrame(-1)">上一帧</el-button>
          <el-button :disabled="!videoReady" @click="stepFrame(1)">下一帧</el-button>
          <span>视频帧 {{ sourceFrame }} · {{ currentTime.toFixed(3) }} s</span>
        </div>
        <el-slider
          v-if="duration > 0"
          v-model="currentTime"
          :max="duration"
          :step="1 / fps"
          :disabled="!videoReady"
          @input="seek"
        />
      </section>

      <section class="repair-panel">
        <el-steps :active="stepIndex" finish-status="success" simple>
          <el-step title="标尺" />
          <el-step title="水面线" />
          <el-step title="方向" />
          <el-step title="事件" />
          <el-step title="帧映射" />
        </el-steps>

        <div class="step-body">
          <template v-if="stepIndex === 0">
            <p>在视频画面上点击参考长度的两个端点。</p>
            <el-input-number v-model="referenceLength" :min="0.001" :precision="3" />
            <span class="unit">米</span>
            <p v-if="scalePixelsPerMeter !== null" class="preview">换算：{{ scalePixelsPerMeter.toFixed(2) }} px/m</p>
            <el-button :disabled="canvasDisabled" @click="clearPoints">清除端点</el-button>
          </template>

          <template v-else-if="stepIndex === 1">
            <p>在画面上点击水面线的两个端点。</p>
            <el-button :disabled="canvasDisabled" @click="clearPoints">清除端点</el-button>
          </template>

          <template v-else-if="stepIndex === 2">
            <el-radio-group v-model="swimDirection">
              <el-radio-button label="left_to_right">左 → 右</el-radio-button>
              <el-radio-button label="right_to_left">右 → 左</el-radio-button>
            </el-radio-group>
          </template>

          <template v-else-if="stepIndex === 3">
            <p>暂停在入水瞬间，点击添加事件。已标记 {{ draftEvents.length }} 个。</p>
            <el-button type="primary" :disabled="!videoReady" @click="addHandEntry">标记当前帧为入水</el-button>
            <div v-for="(event, index) in draftEvents" :key="`${event.frame}-${event.side}`" class="event-row">
              <span>帧 {{ event.frame }} · {{ event.time_sec.toFixed(3) }} s</span>
              <el-button text type="danger" @click="draftEvents.splice(index, 1)">删除</el-button>
            </div>
          </template>

          <template v-else>
            <p>确认标注帧与视频帧的对应关系。</p>
            <el-radio-group v-model="mappingMode">
              <el-radio-button label="affine">固定偏移</el-radio-button>
              <el-radio-button label="identity">同帧对应</el-radio-button>
            </el-radio-group>
            <div v-if="mappingMode === 'affine'" class="mapping-fields">
              <el-input-number v-model="mappingOffset" :step="1" controls-position="right" />
              <span>offset</span>
              <el-input-number v-model="mappingStride" :min="1" :step="1" controls-position="right" />
              <span>stride</span>
            </div>
            <el-checkbox v-model="mappingConfirmed">我已核对标注帧与视频帧</el-checkbox>
            <p class="preview">示例：标注帧 {{ sampleAnnotationFrame }} → 视频帧 {{ mappedSampleFrame }}</p>
          </template>
        </div>

        <div class="step-actions">
          <el-button v-if="stepIndex > 0" @click="stepIndex -= 1">上一步</el-button>
          <el-button v-if="stepIndex < 4" type="primary" @click="stepIndex += 1">下一步</el-button>
          <el-button type="success" :loading="saving" @click="save">保存并重新验证</el-button>
        </div>
        <el-alert v-if="errorMessage" type="error" :title="errorMessage" :closable="false" />
      </section>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getNormalizedAnnotation, repairAnnotationQuality, resolveMediaUrl } from '../../services/api'
import type { QualityRepairPayload, SessionVideo } from '../../types'
import { pixelDistance, toIntrinsicPoint } from './repairGeometry'

const props = defineProps<{
  visible: boolean
  normalizedAnnotationId: number | null
  video: SessionVideo | null
  initialStep?: string
}>()
const emit = defineEmits<{
  (event: 'close'): void
  (event: 'saved'): void
}>()

const videoRef = ref<HTMLVideoElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const videoError = ref(false)
const videoReady = ref(false)
const videoWidth = ref(0)
const videoHeight = ref(0)
const duration = ref(0)
const currentTime = ref(0)
const fps = ref(60)
const sourceFrame = computed(() => Math.max(0, Math.round(currentTime.value * fps.value)))
const stepIndex = ref(0)
const points = ref<Array<{ x: number; y: number }>>([])
const referenceLength = ref<number | null>(25)
const scalePixelsPerMeter = computed(() => {
  if (points.value.length !== 2 || !referenceLength.value || referenceLength.value <= 0) return null
  return (pixelDistance(points.value) || 0) / referenceLength.value
})
const swimDirection = ref<'left_to_right' | 'right_to_left' | undefined>(undefined)
const draftEvents = ref<Array<{ name: string; label: string; frame: number; time_sec: number; side: 'unknown'; confidence: number }>>([])
const mappingMode = ref<'affine' | 'identity'>('affine')
const mappingOffset = ref(0)
const mappingStride = ref(1)
const mappingConfirmed = ref(false)
const annotationRevision = ref(1)
const saving = ref(false)
const errorMessage = ref('')

const videoUrl = computed(() => resolveMediaUrl(props.video?.video?.playback_url))
const canvasDisabled = computed(() => !videoReady.value || videoError.value)
const sampleAnnotationFrame = computed(() => 0)
const mappedSampleFrame = computed(() => mappingMode.value === 'identity' ? 0 : mappingOffset.value)

watch(() => props.visible, async (visible) => {
  if (!visible || !props.normalizedAnnotationId) return
  resetDraft()
  const stepMap: Record<string, number> = { scale: 0, waterline: 1, swim_direction: 2, events: 3, frame_mapping: 4 }
  stepIndex.value = stepMap[props.initialStep || ''] ?? 0
  await nextTick()
  try {
    const detail = await getNormalizedAnnotation(props.normalizedAnnotationId)
    annotationRevision.value = detail.revision
    swimDirection.value = detail.swim_direction as typeof swimDirection.value
    draftEvents.value = (detail.events || []).filter((event) => event.name === 'hand_entry').map((event) => ({
      name: event.name,
      label: event.label || '入水',
      frame: Number(event.frame),
      time_sec: Number(event.time_sec || 0),
      side: event.side || 'unknown',
      confidence: Number(event.confidence ?? 1)
    }))
    const mapping = detail.annotation_metadata?.frame_mapping
    if (mapping) {
      mappingMode.value = mapping.mode === 'identity' ? 'identity' : 'affine'
      mappingOffset.value = Number(mapping.source_frame_offset || 0)
      mappingStride.value = Number(mapping.source_frame_stride || 1)
      mappingConfirmed.value = mapping.verified === true
    }
  } catch {
    errorMessage.value = '无法读取当前标注详情，请刷新后重试。'
  }
}, { immediate: true })

function resetDraft() {
  points.value = []
  errorMessage.value = ''
  videoError.value = false
  videoReady.value = false
  stepIndex.value = 0
  draftEvents.value = []
  mappingConfirmed.value = false
}

function onVideoMetadata() {
  const video = videoRef.value
  if (!video) return
  videoWidth.value = video.videoWidth
  videoHeight.value = video.videoHeight
  duration.value = video.duration || 0
  fps.value = props.video?.fps || 60
  videoReady.value = videoWidth.value > 0 && videoHeight.value > 0
  drawOverlay()
}

function seek(value: number | undefined) {
  if (videoRef.value && value !== undefined) videoRef.value.currentTime = value
  drawOverlay()
}

function onVideoTime() {
  currentTime.value = videoRef.value?.currentTime || 0
  drawOverlay()
}

function stepFrame(direction: number) {
  if (!videoRef.value) return
  videoRef.value.currentTime = Math.max(0, Math.min(duration.value, videoRef.value.currentTime + direction / fps.value))
  currentTime.value = videoRef.value.currentTime
  drawOverlay()
}

function onCanvasClick(event: MouseEvent) {
  if (canvasDisabled.value || (stepIndex.value !== 0 && stepIndex.value !== 1)) return
  const canvas = canvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const point = toIntrinsicPoint(event.clientX, event.clientY, rect, videoWidth.value, videoHeight.value)
  points.value = points.value.length === 2 ? [point] : [...points.value, point]
  drawOverlay()
}

function drawOverlay() {
  const canvas = canvasRef.value
  if (!canvas || !videoWidth.value || !videoHeight.value) return
  const rect = canvas.getBoundingClientRect()
  const ratio = window.devicePixelRatio || 1
  canvas.width = Math.max(1, Math.round(rect.width * ratio))
  canvas.height = Math.max(1, Math.round(rect.height * ratio))
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.scale(ratio, ratio)
  ctx.clearRect(0, 0, rect.width, rect.height)
  const mapped = points.value.map((point) => ({ x: point.x * rect.width / videoWidth.value, y: point.y * rect.height / videoHeight.value }))
  ctx.strokeStyle = '#f5c542'
  ctx.fillStyle = '#f5c542'
  ctx.lineWidth = 3
  if (mapped.length === 2) {
    ctx.beginPath(); ctx.moveTo(mapped[0].x, mapped[0].y); ctx.lineTo(mapped[1].x, mapped[1].y); ctx.stroke()
  }
  mapped.forEach((point) => { ctx.beginPath(); ctx.arc(point.x, point.y, 6, 0, Math.PI * 2); ctx.fill() })
}

function clearPoints() {
  points.value = []
  drawOverlay()
}

function addHandEntry() {
  const frame = sourceFrame.value
  if (draftEvents.value.some((event) => event.frame === frame)) return
  draftEvents.value.push({ name: 'hand_entry', label: '入水', frame, time_sec: currentTime.value, side: 'unknown', confidence: 1 })
  draftEvents.value.sort((a, b) => a.frame - b.frame)
}

function buildPayload(): QualityRepairPayload {
  const payload: QualityRepairPayload = { expected_revision: annotationRevision.value }
  if (points.value.length === 2 && stepIndex.value === 0 && referenceLength.value) {
    payload.scale = { points: points.value, reference_length_m: referenceLength.value, method: 'manual_reference' }
  }
  if (points.value.length === 2 && stepIndex.value === 1) payload.waterline = { points: points.value }
  if (swimDirection.value) payload.swim_direction = swimDirection.value
  if (draftEvents.value.length) payload.events = draftEvents.value
  if (stepIndex.value === 4) {
    payload.frame_mapping = {
      mode: mappingMode.value,
      source_frame_offset: mappingMode.value === 'affine' ? mappingOffset.value : undefined,
      source_frame_stride: mappingMode.value === 'affine' ? mappingStride.value : undefined,
      confirmed: mappingConfirmed.value
    }
  }
  return payload
}

async function save() {
  if (!props.normalizedAnnotationId) return
  errorMessage.value = ''
  if (stepIndex.value <= 1 && points.value.length !== 2) {
    errorMessage.value = '请先在视频画面上选择两个点。'
    return
  }
  if (stepIndex.value === 0 && !referenceLength.value) {
    errorMessage.value = '请输入参考长度。'
    return
  }
  if (stepIndex.value === 4 && !mappingConfirmed.value) {
    errorMessage.value = '请确认帧映射后再保存。'
    return
  }
  saving.value = true
  try {
    await repairAnnotationQuality(props.normalizedAnnotationId, buildPayload())
    ElMessage.success('质量修复已保存，正在使用最新数据重新验证')
    emit('saved')
    emit('close')
  } catch (error: any) {
    if (error?.response?.status === 409 && props.normalizedAnnotationId) {
      try {
        const detail = await getNormalizedAnnotation(props.normalizedAnnotationId)
        annotationRevision.value = detail.revision
      } catch { /* keep the original conflict message */ }
    }
    errorMessage.value = error?.response?.data?.detail?.message || error?.response?.data?.detail || error?.message || '保存失败'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.repair-layout { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(300px, .9fr); gap: 18px; }
.video-frame { position: relative; background: #111; aspect-ratio: 16 / 9; overflow: hidden; }
.video-frame video, .video-frame canvas { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; }
.video-frame video { position: relative; display: block; }
.video-frame canvas { pointer-events: auto; }
.video-frame--error canvas { pointer-events: none; }
.video-error { position: absolute; inset: 0; display: grid; place-items: center; color: #fff; background: rgba(0, 0, 0, .65); }
.frame-controls { display: flex; align-items: center; gap: 8px; margin-top: 10px; color: #606266; font-size: 12px; }
.frame-controls span { margin-left: auto; }
.repair-panel { min-width: 0; }
.step-body { min-height: 220px; padding: 24px 4px 12px; }
.unit { margin-left: 8px; color: #606266; }
.preview { color: #409eff; font-size: 13px; }
.step-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.event-row { display: flex; align-items: center; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #ebeef5; }
.mapping-fields { display: flex; align-items: center; gap: 8px; margin: 18px 0; }
@media (max-width: 760px) { .repair-layout { grid-template-columns: 1fr; } .frame-controls { flex-wrap: wrap; } .frame-controls span { width: 100%; margin-left: 0; } }
</style>
