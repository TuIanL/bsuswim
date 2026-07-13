<template>
  <div class="print-report" :class="{ 'print-report--ready': ready }">
    <div v-if="loading" class="print-state">报告加载中...</div>
    <div v-else-if="error" class="print-state print-state--error">{{ error }}</div>

    <template v-else-if="viewModel">
      <section class="print-page cover-page">
        <ReportSummaryPanel v-if="viewModel.summary" :summary="viewModel.summary" />
      </section>

      <section
        v-for="section in viewModel.sections"
        :key="section.key"
        class="print-page module-page"
      >
        <ReportSectionRenderer :section="section" />
      </section>

      <div class="no-print" style="display:none" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { normalizeReportData } from '../utils/reportAdapter'
import { PrintReadyRegistry } from '../utils/printReadyRegistry'
import type { NormalizedReportViewModel } from '../types/report'
import ReportSectionRenderer from '../components/report/ReportSectionRenderer.vue'
import ReportSummaryPanel from '../components/report/ReportSummaryPanel.vue'

const route = useRoute()
const sessionId = computed(() => route.params.sessionId as string)
const token = computed(() => route.query.token as string)

const loading = ref(true)
const error = ref('')
const viewModel = ref<NormalizedReportViewModel | null>(null)
const ready = ref(false)

onMounted(async () => {
  const registry = new PrintReadyRegistry()
  registry.startTimeout(30000)

  try {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
    const resp = await fetch(
      `${baseUrl}/api/v1/internal/sessions/${sessionId.value}/report/print-data?token=${token.value}`
    )
    if (!resp.ok) throw new Error('打印数据加载失败')
    const data = await resp.json()
    viewModel.value = normalizeReportData(data.report_data)

    await nextTick()

    const images = document.querySelectorAll<HTMLImageElement>('.print-report img')
    images.forEach((img) => {
      const done = registry.addTask(`img:${img.src}`)
      if (img.complete && img.naturalWidth > 0) {
        done()
      } else {
        img.decode().then(done).catch(() => done())
      }
    })

    try {
      await document.fonts.ready
    } catch {
      // font loading not critical
    }

    if (images.length === 0) {
      registry.addTask('immediate')()
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '打印页面加载失败'
  } finally {
    loading.value = false
    ready.value = true
    ;(window as any).__REPORT_PRINT_READY__ = true
  }
})
</script>

<style>
@page {
  size: A4 landscape;
  margin: 0;
}

.print-report {
  width: 297mm;
  min-height: 210mm;
  background: #f7f9fb;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
    "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}

.print-page {
  width: 277mm;
  min-height: 190mm;
  page-break-after: always;
  padding: 10mm;
  margin: 0 auto;
  box-sizing: border-box;
  background: #ffffff;
}

.print-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 210mm;
  font-size: 18px;
  color: #5f6b7a;
}

.print-state--error {
  color: #d9534f;
}

@media print {
  .print-report {
    width: 100%;
  }
  .print-page {
    page-break-after: always;
    page-break-inside: avoid;
  }
}
</style>
