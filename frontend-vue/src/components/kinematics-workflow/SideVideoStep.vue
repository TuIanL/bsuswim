<template>
  <div class="side-video-step">
    <div v-if="video" class="video-bound">
      <el-icon><VideoCamera /></el-icon>
      <div class="video-meta">
        <span class="filename">{{ video.video?.original_filename }}</span>
        <small>
          {{ formatSize(video.video?.size_bytes) }}
          · {{ video.fps || '-' }} FPS
          · {{ video.resolution || '-' }}
          · 已绑定
        </small>
      </div>
      <el-button size="small" text type="warning" @click="$emit('replace')">替换</el-button>
    </div>
    <el-upload
      v-else
      drag
      :auto-upload="false"
      :limit="1"
      accept="video/*"
      :show-file-list="false"
      :on-change="onFile"
    >
      <div>拖入侧面视频或点击选择</div>
      <small>绑定侧面机位后继续后续步骤</small>
    </el-upload>
    <div v-if="file" class="pending-row">
      <span>{{ file.name }}（{{ formatSize(file.size) }}）</span>
      <el-button type="primary" size="small" :loading="uploading" @click="$emit('upload', file)">上传并绑定</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { UploadFile } from 'element-plus'
import type { SessionVideo } from '../../types'

defineProps<{ video: SessionVideo | null; uploading?: boolean }>()
const emit = defineEmits<{ (e: 'file', file: File): void; (e: 'upload', file: File): void; (e: 'replace'): void }>()
const file = ref<File | null>(null)

function onFile(f: UploadFile) {
  if (f.raw) {
    file.value = f.raw
    emit('file', f.raw)
  }
}
function formatSize(bytes?: number) {
  if (!bytes) return '-'
  return bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(0)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
</script>

<style scoped>
.side-video-step { padding: 8px 0; }
.video-bound { display: flex; align-items: center; gap: 12px; }
.video-meta { display: flex; flex-direction: column; flex: 1; }
.filename { font-weight: 500; }
.pending-row { display: flex; align-items: center; justify-content: space-between; margin-top: 8px; }
</style>
