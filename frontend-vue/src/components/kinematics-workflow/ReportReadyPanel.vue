<template>
  <div class="report-ready">
    <el-alert v-if="freshness === 'stale'" type="warning" :closable="false" show-icon>
      <template #title>当前报告基于旧版标注（rev{{ reportRevision }}），当前选择为 rev{{ selectedRevision }}</template>
      <template #default>可查看旧报告，或使用当前标注重新生成。</template>
    </el-alert>

    <el-alert v-if="freshness === 'none'" type="error" :closable="false" show-icon>
      <template #title>报告不可用</template>
      <template #default>分析已完成，但未找到对应的报告数据。可使用当前标注重新生成。</template>
    </el-alert>

    <div v-if="freshness !== 'none'" class="report-actions">
      <el-button type="primary" @click="openHtml">查看 HTML 报告</el-button>
      <el-button :loading="pdfBusy === 'export'" @click="$emit('export-pdf')">
        {{ pdfStatus === 'exported' ? '重新导出 PDF' : '导出 PDF' }}
      </el-button>
      <el-button v-if="pdfStatus === 'exported'" tag="a" :href="pdfUrl" target="_blank">下载 PDF</el-button>
    </div>

    <div v-else class="report-actions">
      <el-button type="warning" :loading="pdfBusy === 'export'" @click="$emit('regenerate')">
        使用当前标注重新生成
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  freshness: 'none' | 'current' | 'stale'
  reportRevision?: number | null
  selectedRevision?: number | null
  pdfStatus?: string
  pdfUrl?: string | null
  pdfBusy?: 'export' | null
}>()
const emit = defineEmits<{ (e: 'open-html'): void; (e: 'export-pdf'): void; (e: 'regenerate'): void }>()
function openHtml() {
  emit('open-html')
}
</script>

<style scoped>
.report-ready { padding: 12px 0; }
.report-actions { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
</style>
