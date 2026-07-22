<template>
  <div class="kinematics-artifacts-section">
    <div v-if="assets.length === 0" class="empty-state">
      <span class="empty-text">暂无可视化资产</span>
    </div>
    <div v-else class="assets-grid">
      <div v-for="asset in assets" :key="asset.key" class="asset-item">
        <div class="asset-preview">
          <img
            v-if="asset.type === 'image' || asset.type === 'annotated_frame'"
            :src="asset.url"
            :alt="asset.title || asset.label"
            loading="lazy"
          />
          <div v-else class="asset-placeholder">
            <span class="asset-type">{{ asset.type }}</span>
          </div>
        </div>
        <div class="asset-info">
          <span class="asset-title">{{ asset.title || asset.label || asset.key }}</span>
          <span v-if="asset.caption" class="asset-caption">{{ asset.caption }}</span>
          <span v-if="asset.value" class="asset-value">{{ asset.value }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ReportAsset } from '../../../types/report'

defineProps<{
  assets: ReportAsset[]
}>()
</script>

<style scoped>
.kinematics-artifacts-section {
  padding: 8px 0;
}

.empty-state {
  text-align: center;
  padding: 16px;
  color: #909399;
}

.assets-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.asset-item {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}

.asset-preview {
  height: 150px;
  background: #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.asset-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.asset-placeholder {
  color: #c0c4cc;
  font-size: 12px;
  text-transform: uppercase;
}

.asset-info {
  padding: 12px;
}

.asset-title {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.asset-caption {
  display: block;
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.asset-value {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #409eff;
}
</style>
