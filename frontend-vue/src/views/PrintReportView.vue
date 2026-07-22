<template>
  <div
    class="print-report"
    :class="{ 'print-report--ready': ready }"
    :data-report-generation-signature="generationSignature"
  >
    <div v-if="loading" class="print-state">报告加载中...</div>
    <div v-else-if="error" class="print-state print-state--error">{{ error }}</div>

    <template v-else-if="viewModel">
      <section
        v-for="section in viewModel.sections"
        :key="section.key"
        class="print-page"
        :data-page-number="section.page_number"
        :data-page-type="section.page_type"
        :data-module-key="section.module_key"
      >
        <span class="print-page-marker" aria-hidden="true">
          P{{ section.page_number }} | {{ section.page_type }}
        </span>
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

const route = useRoute()
const sessionId = computed(() => route.params.sessionId as string)
const token = computed(() => route.query.token as string)

const loading = ref(true)
const error = ref('')
const viewModel = ref<NormalizedReportViewModel | null>(null)
const ready = ref(false)
const generationSignature = ref('')

function fail(code: string, message: string) {
  error.value = message
  ;(window as any).__REPORT_PRINT_ERROR__ = { code, message }
}

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
    const vm = normalizeReportData(data.report_data)
    generationSignature.value = vm.generation_signature || ''
    viewModel.value = vm

    await nextTick()

    // Layout overflow pre-check: a page whose content exceeds its box must
    // block export rather than be silently truncated.
    const pages = Array.from(
      document.querySelectorAll<HTMLElement>('.print-report .print-page')
    )
    for (const page of pages) {
      if (page.scrollHeight > page.clientHeight + 2) {
        fail(
          'PRINT_LAYOUT_OVERFLOW',
          `报告第 ${page.dataset.pageNumber} 页内容溢出，无法导出为固定五页 PDF`
        )
        return
      }
    }

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

    // ready is set only by the registry (all images/fonts/charts done),
    // never unconditionally in a finally block.
    registry.onComplete(() => {
      ready.value = true
      ;(window as any).__REPORT_PRINT_READY__ = true
    })
    registry.onTimeout(() => {
      fail('PRINT_READY_TIMEOUT', '报告资源加载超时，无法导出 PDF')
    })
  } catch (err) {
    fail('PRINT_DATA_LOAD_FAILED', err instanceof Error ? err.message : '打印页面加载失败')
  } finally {
    loading.value = false
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
  break-after: page;
  padding: 10mm;
  margin: 0 auto;
  box-sizing: border-box;
  background: #ffffff;
  position: relative;
}

.print-page:last-child {
  break-after: auto;
}

.print-page-marker {
  position: absolute;
  bottom: 4mm;
  right: 6mm;
  font-size: 9px;
  color: #9aa7b4;
  letter-spacing: 0.5px;
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
    break-after: page;
    break-inside: avoid;
  }
  .print-page:last-child {
    break-after: auto;
  }
}
</style>
