<script setup lang="ts">
import { computed, ref } from 'vue'
import { resolveMediaUrl } from '../../../services/api'
import type { ReportAsset, ReportVideoContext } from '../../../types/report'

const props = defineProps<{
  asset: ReportAsset
  video?: ReportVideoContext
}>()

const showVideo = ref(false)
const videoRef = ref<HTMLVideoElement | null>(null)
const targetFrame = computed(() => props.asset.source_video_frame ?? props.asset.annotation_frame)
const hasVideoEvidence = computed(() => Boolean(
  props.asset.artifact_type === 'annotated_keyframe' &&
  props.video?.playback_url &&
  targetFrame.value !== undefined,
))
const videoUrl = computed(() => resolveMediaUrl(props.video?.playback_url))
const targetSeconds = computed(() => {
  if (targetFrame.value === undefined) return 0
  return Math.max(0, (targetFrame.value - 1) / (props.video?.fps || 60))
})

function openVideo() {
  showVideo.value = true
  window.setTimeout(() => {
    seekTarget()
  }, 0)
}

function seekTarget() {
  if (videoRef.value && videoRef.value.readyState >= 1) {
    videoRef.value.pause()
    videoRef.value.currentTime = targetSeconds.value
  }
}
</script>

<template>
  <article class="evidence-frame-card" :class="asset.status ? `frame--${asset.status}` : ''">
    <div v-if="asset.label || asset.value || asset.metric_label" class="frame-meta">
      <span v-if="asset.metric_label || asset.label" class="frame-label">
        {{ asset.metric_label || asset.label }}
      </span>
      <strong v-if="asset.value !== undefined && asset.value !== null" class="frame-value">
        {{ asset.value }}<span v-if="asset.unit"> {{ asset.unit }}</span>
      </strong>
    </div>

    <div class="frame-image-wrap">
      <img
        v-if="asset.url"
        :src="asset.url"
        :alt="asset.title || asset.label || '关键帧'"
        class="frame-image"
      />
      <div v-else class="frame-placeholder">
        <span>暂无图片</span>
      </div>
    </div>

    <div v-if="asset.title || asset.caption" class="frame-caption">
      <strong v-if="asset.title">{{ asset.title }}</strong>
      <p v-if="asset.caption">{{ asset.caption }}</p>
      <small v-if="asset.selection_reason">{{ asset.selection_reason }}</small>
      <small v-if="asset.annotation_frame !== undefined">
        标注帧 {{ asset.annotation_frame }}<span v-if="asset.source_video_frame !== undefined"> · 视频帧 {{ asset.source_video_frame }}</span>
      </small>
      <small v-if="asset.metadata?.annotation_source">
        {{ asset.metadata.annotation_source }}
      </small>
      <el-button v-if="hasVideoEvidence" class="frame-review" link type="primary" @click="openVideo">
        回看原视频此帧
      </el-button>
    </div>
    <el-dialog v-model="showVideo" title="原视频关键帧复核" width="min(760px, 92vw)" append-to-body>
      <video ref="videoRef" :src="videoUrl" class="review-video" controls preload="metadata" @loadedmetadata="seekTarget" @loadeddata="seekTarget" />
      <p class="review-note">
        已定位到视频第 {{ targetFrame }} 帧（约 {{ targetSeconds.toFixed(2) }} 秒），用于复核关键帧中的动作与骨架位置。
      </p>
    </el-dialog>
  </article>
</template>

<style scoped>
.evidence-frame-card {
  border: 1px solid #e6edf3;
  border-radius: 14px;
  overflow: hidden;
  background: #fff;
}

.frame-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: #f7f9fb;
  border-bottom: 1px solid #e6edf3;
}

.frame-label {
  font-size: 13px;
  color: #5f6b7a;
}

.frame-value {
  font-size: 15px;
}

.frame-image-wrap {
  position: relative;
  width: 100%;
  min-height: 120px;
  background: #f7f9fb;
}

.frame-image {
  width: 100%;
  display: block;
  object-fit: cover;
}

.frame-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 160px;
  color: #a0aebf;
  font-size: 14px;
}

.frame-caption {
  padding: 12px 14px;
  border-top: 1px solid #e6edf3;
}

.frame-caption strong {
  display: block;
  font-size: 14px;
  margin-bottom: 4px;
}

.frame-caption p {
  margin: 0;
  font-size: 13px;
  color: #5f6b7a;
}

.frame-caption small {
  display: block;
  margin-top: 4px;
  color: #7b8794;
  font-size: 11px;
}

.frame-review {
  display: block;
  margin-top: 8px;
  padding: 0;
}

.review-video {
  width: 100%;
  display: block;
  background: #101820;
}

.review-note {
  margin: 10px 0 0;
  color: #5f6b7a;
  font-size: 13px;
}

.frame--good { border-color: #5cb85c; }
.frame--warning { border-color: #f0ad4e; }
.frame--poor { border-color: #d9534f; }
</style>
