<template>
  <canvas ref="canvasRef" />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import type { AnalysisResult } from '../types'

const props = defineProps<{
  result?: AnalysisResult
  video?: HTMLVideoElement | null
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
let frameId = 0

function nearestFrame(time: number) {
  const frames = props.result?.keypoint_frames || []
  if (!frames.length) return undefined
  return frames.reduce((best, item) => (Math.abs(item.time - time) < Math.abs(best.time - time) ? item : best), frames[0])
}

function nearestDetection(time: number) {
  const detections = props.result?.detections || []
  if (!detections.length) return undefined
  return detections.reduce((best, item) => (Math.abs(item.time - time) < Math.abs(best.time - time) ? item : best), detections[0])
}

function draw() {
  const canvas = canvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  canvas.width = Math.max(1, Math.floor(rect.width * window.devicePixelRatio))
  canvas.height = Math.max(1, Math.floor(rect.height * window.devicePixelRatio))
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  ctx.scale(window.devicePixelRatio, window.devicePixelRatio)
  ctx.clearRect(0, 0, rect.width, rect.height)

  const time = props.video?.currentTime || 0
  const detection = nearestDetection(time)
  const frame = nearestFrame(time)

  if (detection?.bbox) {
    const [x, y, w, h] = detection.bbox
    ctx.strokeStyle = '#43d6c9'
    ctx.lineWidth = 2
    ctx.strokeRect(x * rect.width, y * rect.height, w * rect.width, h * rect.height)
    ctx.fillStyle = '#43d6c9'
    ctx.font = '13px sans-serif'
    ctx.fillText(`${detection.label || 'swimmer'} ${(detection.confidence || 0).toFixed(2)}`, x * rect.width, y * rect.height - 8)
  }

  const points = frame?.points || []
  if (points.length) {
    ctx.strokeStyle = '#f5c542'
    ctx.lineWidth = 2
    ctx.beginPath()
    points.forEach((point: any, index: number) => {
      const px = point.x * rect.width
      const py = point.y * rect.height
      if (index === 0) ctx.moveTo(px, py)
      else ctx.lineTo(px, py)
    })
    ctx.stroke()

    points.forEach((point: any) => {
      const px = point.x * rect.width
      const py = point.y * rect.height
      ctx.beginPath()
      ctx.fillStyle = '#ffffff'
      ctx.arc(px, py, 4, 0, Math.PI * 2)
      ctx.fill()
    })
  }

  const phase = props.result?.phases.find((item: any) => time >= item.start && time <= item.end)
  if (phase) {
    ctx.fillStyle = 'rgba(15, 31, 46, 0.72)'
    ctx.fillRect(14, 14, 180, 34)
    ctx.fillStyle = '#dff8ff'
    ctx.font = '14px sans-serif'
    ctx.fillText(phase.label, 26, 36)
  }

  frameId = requestAnimationFrame(draw)
}

onMounted(draw)
onUnmounted(() => cancelAnimationFrame(frameId))
watch(() => props.result, draw)
</script>
