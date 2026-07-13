<script setup lang="ts">
import type { ReportFinding } from '../../../types/report'

defineProps<{
  items: ReportFinding[]
  title?: string
}>()

function severityClass(severity?: string): string {
  if (severity === 'high') return 'severity-high'
  if (severity === 'medium') return 'severity-medium'
  return 'severity-low'
}
</script>

<template>
  <div class="finding-list">
    <h3 v-if="title" class="finding-list__title">{{ title }}</h3>
    <ul>
      <li
        v-for="(item, i) in items"
        :key="item.key ?? i"
        class="finding-item"
        :class="severityClass(item.severity)"
      >
        <div class="finding-item__head">
          <span v-if="item.severity" class="severity-dot" :class="severityClass(item.severity)" />
          <strong v-if="item.title">{{ item.title }}</strong>
        </div>
        <p v-if="item.evidence" class="finding-item__evidence">{{ item.evidence }}</p>
        <p v-else-if="item.content" class="finding-item__content">{{ item.content }}</p>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.finding-list {
  margin-bottom: 0;
}

.finding-list__title {
  font-size: 16px;
  font-weight: 700;
  margin: 0 0 12px;
}

.finding-list ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.finding-item {
  padding: 12px 16px;
  border: 1px solid #e6edf3;
  border-radius: 10px;
  margin-bottom: 8px;
  transition: border-color 0.15s;
}

.finding-item__head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.severity-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.severity-high { border-color: #d9534f; }
.severity-high .severity-dot { background: #d9534f; }

.severity-medium { border-color: #f0ad4e; }
.severity-medium .severity-dot { background: #f0ad4e; }

.severity-low { border-color: #5cb85c; }
.severity-low .severity-dot { background: #5cb85c; }

.finding-item__evidence,
.finding-item__content {
  margin: 4px 0 0;
  font-size: 14px;
  color: #5f6b7a;
  line-height: 1.5;
}
</style>
