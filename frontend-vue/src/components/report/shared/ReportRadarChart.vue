<script setup lang="ts">
import * as echarts from 'echarts'
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps<{
  data: { name: string; value: number }[]
  printMode?: boolean
  onReady?: () => void
}>()

const chartRef = ref<HTMLDivElement | null>(null)
const imageUrl = ref('')
const emit = defineEmits<{
  (e: 'ready'): void
}>()

let chart: echarts.ECharts | null = null

function render() {
  if (!chartRef.value || !props.data?.length) return
  chart?.dispose()
  chart = echarts.init(chartRef.value)
  chart.setOption({
    radar: {
      indicator: props.data.map((item) => ({ name: item.name, max: 100 })),
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: props.data.map((item) => item.value),
            name: '技术评分',
          },
        ],
      },
    ],
  })

  if (props.printMode) {
    chart.on('finished', () => {
      chart?.resize()
      const url = chart?.getDataURL({
        type: 'png',
        pixelRatio: 2,
        backgroundColor: '#ffffff',
      })
      if (url) {
        imageUrl.value = url
        chart?.dispose()
        chart = null
      }
      props.onReady?.()
      emit('ready')
    })
  }
}

onMounted(() => {
  nextTick(render)
})

watch(
  () => props.data,
  () => nextTick(render),
  { deep: true }
)

onUnmounted(() => {
  chart?.dispose()
})
</script>

<template>
  <div v-if="!printMode && data?.length" ref="chartRef" class="radar-chart" />
  <img
    v-else-if="printMode && imageUrl"
    :src="imageUrl"
    class="radar-chart-image"
    alt="技术评分雷达图"
  />
</template>

<style scoped>
.radar-chart {
  width: 100%;
  height: 320px;
  margin-top: 20px;
}

.radar-chart-image {
  width: 100%;
  height: auto;
  max-height: 260px;
  object-fit: contain;
}
</style>
