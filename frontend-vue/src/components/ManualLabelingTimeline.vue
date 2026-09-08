<script setup lang="ts">
import { computed } from 'vue'
import type { ManualPhaseSegment, PhaseCode } from '../types'

const props = defineProps<{
  side: 'left' | 'right'
  segments: ManualPhaseSegment[]
  durationSec: number
  editable: boolean
}>()

const emit = defineEmits<{
  (e: 'create-at', side: 'left' | 'right', timeSec: number): void
  (e: 'select', segment: ManualPhaseSegment): void
}>()

const phaseColor: Record<PhaseCode, string> = {
  entry: '#3b82f6',
  catch: '#10b981',
  push: '#f59e0b',
  recovery: '#a855f7'
}

const phaseDisplay: Record<PhaseCode, string> = {
  entry: '入水',
  catch: '抱水',
  push: '推水',
  recovery: '移臂'
}

// 按 cycle_id 分组，便于展示同一周期的连续阶段
const grouped = computed(() => {
  const map = new Map<string, ManualPhaseSegment[]>()
  for (const s of props.segments) {
    if (s.side !== props.side) continue
    const arr = map.get(s.cycle_id) || []
    arr.push(s)
    map.set(s.cycle_id, arr)
  }
  return Array.from(map.entries()).map(([cycleId, segs]) => ({
    cycleId,
    segs: segs.slice().sort((a, b) => a.start_time_sec - b.start_time_sec)
  }))
})

function pct(t: number): string {
  if (!props.durationSec) return '0%'
  return `${Math.min(100, Math.max(0, (t / props.durationSec) * 100))}%`
}

function onClickTrack(ev: MouseEvent) {
  if (!props.editable) return
  const track = ev.currentTarget as HTMLElement
  const rect = track.getBoundingClientRect()
  const ratio = (ev.clientX - rect.left) / rect.width
  emit('create-at', props.side, ratio * props.durationSec)
}
</script>

<template>
  <div class="timeline-block">
    <div class="timeline-head">
      <span class="side-badge" :class="side">{{ side === 'left' ? '左臂' : '右臂' }}</span>
      <span class="cycle-count">{{ grouped.length }} 个周期</span>
    </div>

    <div
      v-for="g in grouped"
      :key="g.cycleId"
      class="cycle-row"
    >
      <span class="cycle-label">{{ g.cycleId.slice(0, 8) }}</span>
      <div class="track" @click="onClickTrack">
        <div
          v-for="seg in g.segs"
          :key="seg.id"
          class="seg"
          :style="{
            left: pct(seg.start_time_sec),
            width: pct(Math.max(0, seg.end_time_sec - seg.start_time_sec)),
            background: phaseColor[seg.phase_code]
          }"
          :title="`${phaseDisplay[seg.phase_code]} ${seg.start_time_sec.toFixed(2)}–${seg.end_time_sec.toFixed(2)}s`"
          @click.stop="emit('select', seg)"
        >
          <span class="seg-label">{{ phaseDisplay[seg.phase_code] }}</span>
        </div>
      </div>
    </div>

    <div v-if="grouped.length === 0" class="empty-hint">
      暂无 {{ side === 'left' ? '左臂' : '右臂' }} 标注，点击轨道以当前播放位置创建区间
    </div>
  </div>
</template>

<style scoped>
.timeline-block {
  border: 1px solid #2a3550;
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 12px;
  background: #0f172a;
}
.timeline-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.side-badge {
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
}
.side-badge.left {
  background: #1e3a8a;
  color: #bfdbfe;
}
.side-badge.right {
  background: #7c2d12;
  color: #fed7aa;
}
.cycle-count {
  color: #94a3b8;
  font-size: 12px;
}
.cycle-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 6px 0;
}
.cycle-label {
  width: 64px;
  font-size: 11px;
  color: #64748b;
  font-family: monospace;
}
.track {
  position: relative;
  flex: 1;
  height: 26px;
  background: #1e293b;
  border-radius: 4px;
  cursor: pointer;
}
.seg {
  position: absolute;
  top: 2px;
  bottom: 2px;
  border-radius: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  cursor: pointer;
}
.seg-label {
  font-size: 10px;
  color: #fff;
  white-space: nowrap;
}
.empty-hint {
  color: #64748b;
  font-size: 12px;
  padding: 6px 0;
}
</style>
