<template>
  <div class="kinematics-artifacts-panel">
    <div class="panel-header">
      <h3>可视化分析</h3>
      <div class="panel-actions">
        <el-button size="small" @click="refresh" :loading="loading">刷新</el-button>
        <el-button size="small" type="primary" @click="regenerate" :loading="generating">
          重新生成
        </el-button>
      </div>
    </div>

    <div v-if="loading" class="panel-loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载可视化数据...</span>
    </div>

    <div v-else-if="generating" class="panel-loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>正在生成可视化...</span>
    </div>

    <div v-else-if="error" class="panel-error">
      <el-alert :title="error" type="error" show-icon :closable="false" />
      <el-button size="small" @click="refresh">重试</el-button>
    </div>

    <div v-else-if="!hasArtifacts" class="panel-empty">
      <el-empty description="暂无可视化数据" :image-size="80" />
    </div>

    <template v-else>
      <div class="artifacts-grid">
        <div
          v-for="artifact in readyArtifacts"
          :key="artifact.asset_url"
          class="artifact-item"
          @click="openPreview(artifact)"
        >
          <div class="artifact-preview">
            <img
              v-if="artifact.asset_type?.startsWith('image/')"
              :src="resolveMediaUrl(artifact.asset_url)"
              :alt="artifact.artifact_key"
              loading="lazy"
            />
            <div v-else class="artifact-placeholder">
              <el-icon size="24"><Document /></el-icon>
            </div>
          </div>
          <div class="artifact-info">
            <span class="artifact-key">{{ artifact.artifact_key }}</span>
            <span class="artifact-module">{{ artifact.module_key }}</span>
          </div>
        </div>
      </div>

      <div v-if="skippedArtifacts.length > 0" class="skipped-section">
        <h4>未生成的项目</h4>
        <div class="skipped-list">
          <div v-for="artifact in skippedArtifacts" :key="artifact.artifact_key" class="skipped-item">
            <span class="skipped-key">{{ artifact.artifact_key }}</span>
            <span class="skipped-reason">{{ artifact.skip_reason || artifact.status }}</span>
          </div>
        </div>
      </div>
    </template>

    <!-- Preview Dialog -->
    <el-dialog v-model="previewVisible" :title="previewArtifact?.artifact_key" width="80%">
      <img
        v-if="previewArtifact?.asset_type?.startsWith('image/')"
        :src="resolveMediaUrl(previewArtifact?.asset_url)"
        :alt="previewArtifact?.artifact_key"
        style="width: 100%;"
      />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Loading, Document } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getKinematicArtifacts, generateKinematicArtifacts, resolveMediaUrl } from '../../services/api'
import type { KinematicArtifact, KinematicArtifactSetRead } from '../../types'

const props = defineProps<{
  annotationMetricId: number
}>()

const loading = ref(false)
const generating = ref(false)
const error = ref('')
const artifactSet = ref<KinematicArtifactSetRead | null>(null)
const previewVisible = ref(false)
const previewArtifact = ref<KinematicArtifact | null>(null)

const hasArtifacts = computed(() => {
  return artifactSet.value && artifactSet.value.artifacts.length > 0
})

const readyArtifacts = computed(() => {
  return artifactSet.value?.artifacts.filter(a => a.status === 'ready' && a.asset_url) || []
})

const skippedArtifacts = computed(() => {
  return artifactSet.value?.artifacts.filter(a => a.status !== 'ready') || []
})

function openPreview(artifact: KinematicArtifact) {
  previewArtifact.value = artifact
  previewVisible.value = true
}

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    artifactSet.value = await getKinematicArtifacts(props.annotationMetricId)
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || '加载可视化数据失败'
  } finally {
    loading.value = false
  }
}

async function regenerate() {
  generating.value = true
  try {
    await generateKinematicArtifacts(props.annotationMetricId, true)
    await refresh()
    ElMessage.success('可视化已重新生成')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '生成可视化失败')
  } finally {
    generating.value = false
  }
}

onMounted(refresh)
</script>

<style scoped>
.kinematics-artifacts-panel {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  background: #fff;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.panel-actions {
  display: flex;
  gap: 8px;
}

.panel-loading,
.panel-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
  color: #909399;
}

.panel-error {
  padding: 16px;
}

.artifacts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.artifact-item {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s;
}

.artifact-item:hover {
  border-color: #409eff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.1);
}

.artifact-preview {
  height: 150px;
  background: #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.artifact-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.artifact-placeholder {
  color: #c0c4cc;
}

.artifact-info {
  padding: 12px;
  background: #fff;
}

.artifact-key {
  display: block;
  font-size: 12px;
  color: #303133;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.artifact-module {
  font-size: 11px;
  color: #909399;
}

.skipped-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}

.skipped-section h4 {
  font-size: 14px;
  color: #606266;
  margin: 0 0 12px 0;
}

.skipped-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skipped-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  background: #fef0f0;
  border-radius: 4px;
  font-size: 12px;
}

.skipped-key {
  color: #606266;
}

.skipped-reason {
  color: #f56c6c;
}
</style>
