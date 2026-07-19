<template>
  <div class="cvat-step">
    <el-upload
      drag
      :auto-upload="false"
      :limit="1"
      accept=".xml"
      :show-file-list="false"
      :on-change="onFile"
    >
      <div>上传 CVAT 骨架标注（.xml）</div>
      <small>解析后将展示标注质量与四类模块可用性</small>
    </el-upload>

    <div v-if="ingesting" class="ingesting">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>上传并解析中……</span>
    </div>

    <div v-if="parseError" class="parse-error">{{ parseError }}</div>

    <div v-if="annotations.length" class="ann-list">
      <div v-for="ann in annotations" :key="ann.id" class="ann-item" :class="{ selected: ann.normalized_annotation_id === selectedId }">
        <el-radio :value="ann.normalized_annotation_id" :disabled="!isSelectable(ann)" @change="onSelect(ann)">
          <span class="ann-name">{{ ann.original_filename }}</span>
          <small>v{{ ann.version }} · rev{{ ann.normalized_revision }}</small>
          <el-tag size="small" :type="qualityTag(ann.quality_status)">{{ qualityLabel(ann.quality_status) }}</el-tag>
        </el-radio>
        <div class="ann-actions">
          <el-button v-if="ann.status === 'parse_failed'" size="small" text type="primary" :loading="reparsingId === ann.id" @click="$emit('reparse', ann.id)">重新解析</el-button>
          <el-button v-if="ann.quality_status === 'invalid'" size="small" text type="warning" @click="$emit('replace', ann)">替换</el-button>
        </div>
      </div>
    </div>
    <el-empty v-else description="暂无标注文件" :image-size="40" />

    <div v-if="selected && selected.parse_summary" class="parse-summary">
      <span>标注帧 {{ selected.parse_summary.keypoint_frames_count }}</span>
      <span>事件 {{ selected.parse_summary.events_count }}</span>
      <span>轨迹 {{ selected.parse_summary.trajectories_count }}</span>
      <span>人工标签 {{ selected.parse_summary.manual_tags_count }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { AnnotationFileListItem } from '../../types'

const props = defineProps<{
  annotations: AnnotationFileListItem[]
  selectedId: number | null
  ingesting?: boolean
  parseError?: string | null
  reparsingId?: number | null
}>()
const emit = defineEmits<{
  (e: 'file', file: File): void
  (e: 'select', id: number): void
  (e: 'reparse', id: number): void
  (e: 'replace', ann: AnnotationFileListItem): void
}>()

import type { UploadFile } from 'element-plus'
function onFile(f: UploadFile) {
  if (f.raw) emit('file', f.raw)
}
function isSelectable(ann: AnnotationFileListItem) {
  return ann.status === 'parsed' && ann.quality_status && ann.quality_status !== 'invalid' && ann.normalized_annotation_id != null
}
function onSelect(ann: AnnotationFileListItem) {
  if (ann.normalized_annotation_id != null) emit('select', ann.normalized_annotation_id)
}
import { computed } from 'vue'
const selected = computed(() => props.annotations.find((a) => a.normalized_annotation_id === props.selectedId) ?? null)
function qualityTag(s?: string) {
  return s === 'valid' ? 'success' : s === 'warning' ? 'warning' : s === 'invalid' ? 'danger' : 'info'
}
function qualityLabel(s?: string) {
  return s === 'valid' ? '可分析' : s === 'warning' ? '警告' : s === 'invalid' ? '不可分析' : '未知'
}
</script>

<style scoped>
.cvat-step { padding: 8px 0; }
.ingesting, .parse-error { display: flex; align-items: center; gap: 8px; padding: 8px 0; color: #909399; font-size: 13px; }
.parse-error { color: #f56c6c; }
.ann-list { margin-top: 12px; display: flex; flex-direction: column; gap: 8px; }
.ann-item { display: flex; align-items: center; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #f2f2f2; }
.ann-item.selected { background: #ecf5ff; }
.ann-name { font-weight: 500; margin-right: 6px; }
.ann-actions { display: flex; gap: 4px; }
.parse-summary { display: flex; gap: 16px; margin-top: 10px; font-size: 13px; color: #606266; }
</style>
