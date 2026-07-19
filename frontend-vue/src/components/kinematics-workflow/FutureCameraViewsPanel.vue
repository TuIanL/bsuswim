<template>
  <el-collapse class="future-cameras">
    <el-collapse-item title="后续扩展机位（本次不参与分析）">
      <div v-for="cam in cameras" :key="cam.view" class="future-card">
        <div class="future-head">
          <span class="future-label">{{ cam.label }}</span>
          <el-tag size="small" type="info">后续扩展</el-tag>
        </div>
        <p class="future-desc">{{ cam.description }}</p>
        <p v-if="cam.hasVideo" class="future-note">已有素材，本次不参与分析</p>
      </div>
    </el-collapse-item>
  </el-collapse>
</template>

<script setup lang="ts">
import type { SessionVideo } from '../../types'

const props = defineProps<{ videos: SessionVideo[] }>()

const cameras = [
  { view: 'front', label: '正面机位', description: '左右对称与入水宽度' },
  { view: 'top', label: '俯视机位', description: '路线与偏航' },
  { view: 'underwater', label: '水下机位', description: '抱水与推进路径' },
  { view: 'semi_underwater', label: '半水下机位', description: '水面交界动作' }
].map((c) => ({
  ...c,
  hasVideo: props.videos.some((v) => v.view_type === c.view)
}))
</script>

<style scoped>
.future-cameras { margin-top: 16px; }
.future-card { padding: 8px 0; border-bottom: 1px solid #f2f2f2; }
.future-head { display: flex; align-items: center; gap: 8px; }
.future-label { font-weight: 500; }
.future-desc { font-size: 13px; color: #606266; margin: 4px 0; }
.future-note { font-size: 12px; color: #909399; }
</style>
