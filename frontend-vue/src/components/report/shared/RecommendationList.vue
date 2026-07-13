<script setup lang="ts">
import type { ReportRecommendation } from '../../../types/report'

defineProps<{
  items: ReportRecommendation[]
  title?: string
}>()
</script>

<template>
  <div class="recommendation-list">
    <h3 v-if="title" class="recommendation-list__title">{{ title }}</h3>
    <ul>
      <li
        v-for="(item, i) in items"
        :key="item.key ?? i"
        class="recommendation-item"
      >
        <strong v-if="item.title" class="recommendation-item__title">
          {{ item.title }}
        </strong>
        <p class="recommendation-item__content">{{ item.content }}</p>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.recommendation-list__title {
  font-size: 16px;
  font-weight: 700;
  margin: 0 0 12px;
}

.recommendation-list ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.recommendation-item {
  padding: 12px 16px;
  border: 1px solid #e6edf3;
  border-radius: 10px;
  margin-bottom: 8px;
  background: #f7f9fb;
}

.recommendation-item__title {
  display: block;
  font-size: 14px;
  margin-bottom: 4px;
}

.recommendation-item__content {
  margin: 0;
  font-size: 14px;
  color: #5f6b7a;
  line-height: 1.5;
}
</style>
