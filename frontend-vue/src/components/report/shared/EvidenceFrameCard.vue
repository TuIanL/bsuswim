<script setup lang="ts">
import type { ReportAsset } from '../../../types/report'

defineProps<{
  asset: ReportAsset
}>()
</script>

<template>
  <article class="evidence-frame-card" :class="asset.status ? `frame--${asset.status}` : ''">
    <div v-if="asset.label || asset.value" class="frame-meta">
      <span v-if="asset.label" class="frame-label">{{ asset.label }}</span>
      <strong v-if="asset.value" class="frame-value">{{ asset.value }}</strong>
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
    </div>
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

.frame--good { border-color: #5cb85c; }
.frame--warning { border-color: #f0ad4e; }
.frame--poor { border-color: #d9534f; }
</style>
