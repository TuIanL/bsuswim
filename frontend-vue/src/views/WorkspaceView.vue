<template>
  <div>
    <div class="page-head">
      <div>
        <h1>可视化工作台</h1>
        <p>{{ workspaceTitle }}</p>
      </div>
      <el-button :disabled="data?.task.status !== 'completed'" type="primary" @click="$router.push(`/reports/${data?.task.session_id}`)">查看报告</el-button>
    </div>

    <div v-if="loading" class="section">加载中...</div>
    <div v-else-if="data" class="grid-two">
      <div class="section">
        <div class="video-stage">
          <video
            v-if="videoUrl"
            ref="videoRef"
            controls
            :src="videoUrl"
            @error="videoError = true"
          />
          <div v-else class="placeholder-water">Demo 可视化画布</div>
          <OverlayCanvas :result="supportedResult ? data.result || undefined : undefined" :video="videoRef" />
        </div>
        <el-alert v-if="!supportedResult" class="mt" title="当前结果不可用或 schema 不兼容" type="warning" :closable="false" />
        <el-alert v-if="videoError" class="mt" title="视频资源无法加载，但任务元数据仍可查看" type="error" :closable="false" />
        <el-alert v-if="data.task.error_message" class="mt" :title="data.task.error_message" type="error" :closable="false" />
      </div>

      <div class="section">
        <h2>任务状态</h2>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="状态">{{ data.task.status }}</el-descriptions-item>
          <el-descriptions-item label="阶段">{{ data.task.stage }}</el-descriptions-item>
          <el-descriptions-item label="进度">{{ data.task.progress }}%</el-descriptions-item>
          <el-descriptions-item label="来源">{{ data.result ? data.result.schema_version : '暂无结果' }}</el-descriptions-item>
          <el-descriptions-item label="训练记录">{{ data.task.session_id }}</el-descriptions-item>
        </el-descriptions>
        <h2>视频资源</h2>
        <el-tag v-for="video in data.session_videos || []" :key="video.id" class="video-tag">
          {{ video.view_type }} · {{ video.video.original_filename }}
        </el-tag>
        <h2>核心指标</h2>
        <div class="metric-grid">
          <div v-for="(value, key) in data.result?.metrics || {}" :key="key" class="metric">
            <span>{{ key }}</span>
            <strong>{{ value }}</strong>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import OverlayCanvas from '../components/OverlayCanvas.vue'
import { getAnalysisWorkspace, resolveMediaUrl } from '../services/api'
import type { WorkspaceData } from '../types'

const props = defineProps<{ taskId: string }>()
const data = ref<WorkspaceData | null>(null)
const loading = ref(true)
const videoRef = ref<HTMLVideoElement | null>(null)
const videoError = ref(false)
let timer = 0

const supportedResult = computed(() => data.value?.result?.schema_version === 'swim-analysis.v1')
const workspaceTitle = computed(() => {
  const payloadTitle = data.value?.task.request_payload?.session?.title
  return payloadTitle || data.value?.task.session_metadata?.session_title || '加载分析任务'
})
const primaryVideo = computed(() => data.value?.session_videos?.[0]?.video || data.value?.videos?.[0] || data.value?.task.video)
const videoUrl = computed(() => resolveMediaUrl(primaryVideo.value?.playback_url))

async function load() {
  const taskId = Number(props.taskId)
  data.value = await getAnalysisWorkspace(taskId)
  loading.value = false
  if (data.value.task.status === 'completed' || data.value.task.status === 'failed') {
    window.clearInterval(timer)
  }
}

onMounted(async () => {
  await load()
  timer = window.setInterval(load, 3000)
})

onUnmounted(() => window.clearInterval(timer))
</script>

<style scoped>
.mt {
  margin-top: 12px;
}

.video-tag {
  margin: 8px 8px 0 0;
}
</style>
