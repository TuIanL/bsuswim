<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import {
  listManualAnnotationSets,
  createManualAnnotationSet,
  getManualAnnotationRevision,
  listManualPhaseSegments,
  createManualPhaseSegment,
  updateManualPhaseSegment,
  deleteManualPhaseSegment,
  forkManualAnnotationRevision,
  submitReviewManualRevision,
  reviewPassManualRevision,
  rejectManualRevision,
  freezeManualRevision,
  getPhaseProfile
} from '../services/api'
import ManualLabelingTimeline from '../components/ManualLabelingTimeline.vue'
import type {
  ManualAnnotationSet,
  ManualAnnotationRevision,
  ManualPhaseSegment,
  PhaseProfile,
  PhaseCode,
  SegmentSide
} from '../types'

const props = defineProps<{
  sessionId: string
  sessionVideoId: string
}>()

const sessionVideoIdNum = Number(props.sessionVideoId)

const annotationSet = ref<ManualAnnotationSet | null>(null)
const revision = ref<ManualAnnotationRevision | null>(null)
const segments = ref<ManualPhaseSegment[]>([])
const profile = ref<PhaseProfile | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const lockConflict = ref(false) // 乐观锁 409 提示刷新

const currentTime = ref(0)
const durationSec = ref(0)

const phaseDisplayMap = computed<Record<string, string>>(() => {
  const m: Record<string, string> = {}
  profile.value?.phases.forEach((p) => (m[p.code] = p.display))
  return m
})

const isDraft = computed(() => revision.value?.status === 'draft')
const editable = computed(() => isDraft.value)

// ── 表单 ──
const form = ref({
  cycle_id: '',
  side: 'left' as SegmentSide,
  phase_code: 'entry' as PhaseCode,
  start_time_sec: 0,
  end_time_sec: 0,
  confidence: null as number | null,
  note: ''
})
const editingSegmentId = ref<number | null>(null)
const showGuidance = ref<string | null>(null)

function newCycleId(): string {
  return (crypto.randomUUID?.() ?? `c-${Date.now()}-${Math.random().toString(16).slice(2)}`)
}

const phaseToBoundary: Record<PhaseCode, string> = {
  entry: 'hand_entry',
  catch: 'catch_start',
  push: 'pull_end',
  recovery: 'hand_exit'
}
function boundaryNameFor(code: string): string {
  return phaseToBoundary[code as PhaseCode] || code
}

async function ensureSetAndLoad() {
  loading.value = true
  error.value = null
  try {
    let sets = await listManualAnnotationSets(sessionVideoIdNum)
    if (!sets.length) {
      const created = await createManualAnnotationSet(sessionVideoIdNum)
      sets = [created]
    }
    annotationSet.value = sets[0]
    const revId = annotationSet.value.head_revision_id
    if (revId) {
      revision.value = await getManualAnnotationRevision(revId)
      segments.value = await listManualPhaseSegments(revId)
    }
    profile.value = await getPhaseProfile(annotationSet.value.phase_profile_id)
  } catch (e: any) {
    error.value = e?.response?.data?.detail?.message || e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function resetForm() {
  editingSegmentId.value = null
  form.value = {
    cycle_id: '',
    side: 'left',
    phase_code: 'entry',
    start_time_sec: currentTime.value,
    end_time_sec: currentTime.value + 0.5,
    confidence: null,
    note: ''
  }
}

function useCurrentPosition() {
  form.value.start_time_sec = Number(currentTime.value.toFixed(3))
  form.value.end_time_sec = Number((currentTime.value + 0.5).toFixed(3))
}

async function submitForm() {
  if (!revision.value) return
  lockConflict.value = false
  const payload = {
    ...form.value,
    edit_version: revision.value.edit_version
  }
  try {
    if (editingSegmentId.value != null) {
      await updateManualPhaseSegment(editingSegmentId.value, payload)
    } else {
      const cycleId = form.value.cycle_id || newCycleId()
      await createManualPhaseSegment(revision.value.id, { ...payload, cycle_id: cycleId })
    }
    await refreshRevision()
    resetForm()
  } catch (e: any) {
    handleWriteError(e)
  }
}

async function removeSegment(seg: ManualPhaseSegment) {
  if (!revision.value) return
  try {
    await deleteManualPhaseSegment(seg.id, revision.value.edit_version)
    await refreshRevision()
  } catch (e: any) {
    handleWriteError(e)
  }
}

function selectForEdit(seg: ManualPhaseSegment) {
  if (!editable.value) return
  editingSegmentId.value = seg.id
  form.value = {
    cycle_id: seg.cycle_id,
    side: seg.side,
    phase_code: seg.phase_code,
    start_time_sec: seg.start_time_sec,
    end_time_sec: seg.end_time_sec,
    confidence: seg.confidence,
    note: seg.note || ''
  }
}

function handleWriteError(e: any) {
  if (e?.response?.status === 409) {
    lockConflict.value = true
    error.value = '内容已被他人修改（edit_version 不匹配），请刷新页面后再操作。'
  } else {
    error.value = e?.response?.data?.detail?.message || e?.message || '写操作失败'
  }
}

async function refreshRevision() {
  if (!revision.value) return
  revision.value = await getManualAnnotationRevision(revision.value.id)
  segments.value = await listManualPhaseSegments(revision.value.id)
}

async function runLifecycle(action: 'submit' | 'pass' | 'reject' | 'freeze' | 'fork') {
  if (!revision.value) return
  error.value = null
  lockConflict.value = false
  const map = {
    submit: submitReviewManualRevision,
    pass: reviewPassManualRevision,
    reject: rejectManualRevision,
    freeze: freezeManualRevision,
    fork: forkManualAnnotationRevision
  }
  try {
    await map[action](revision.value.id)
    await refreshRevision()
  } catch (e: any) {
    error.value = e?.response?.data?.detail?.message || e?.message || '生命周期操作失败'
  }
}

const leftSegments = computed(() => segments.value.filter((s) => s.side === 'left'))
const rightSegments = computed(() => segments.value.filter((s) => s.side === 'right'))

onMounted(() => {
  resetForm()
  ensureSetAndLoad()
})
</script>

<template>
  <div class="labeling-view">
    <header class="lv-head">
      <h2>人工动作周期标注工作台</h2>
      <div class="meta">
        <span v-if="revision">revision #{{ revision.revision_no }} · {{ revision.status }}</span>
        <span v-if="revision">· 阶段数 {{ revision.segment_count }} · 周期数 {{ revision.cycle_count }}</span>
        <span v-if="profile">· profile {{ profile.id }} {{ profile.version }}</span>
      </div>
    </header>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="lockConflict" class="error">乐观锁冲突：请刷新后再操作，系统不会自动覆盖。</p>

    <section class="player">
      <label>播放位置 (s): {{ currentTime.toFixed(2) }}</label>
      <input type="range" min="0" :max="durationSec || 100" step="0.01" v-model.number="currentTime" />
      <button v-if="editable" @click="useCurrentPosition">使用当前位置填入起点</button>
    </section>

    <section class="timelines">
      <ManualLabelingTimeline
        side="left"
        :segments="segments"
        :duration-sec="durationSec"
        :editable="editable"
        @create-at="(s, t) => { form.side = s; form.start_time_sec = Number(t.toFixed(3)); form.end_time_sec = Number((t + 0.5).toFixed(3)) }"
        @select="selectForEdit"
      />
      <ManualLabelingTimeline
        side="right"
        :segments="segments"
        :duration-sec="durationSec"
        :editable="editable"
        @create-at="(s, t) => { form.side = s; form.start_time_sec = Number(t.toFixed(3)); form.end_time_sec = Number((t + 0.5).toFixed(3)) }"
        @select="selectForEdit"
      />
    </section>

    <section class="editor" v-if="editable">
      <h3>{{ editingSegmentId != null ? '编辑区间' : '新建区间' }}</h3>
      <div class="form-grid">
        <label>周期 cycle_id
          <input v-model="form.cycle_id" placeholder="留空=新建周期" />
        </label>
        <label>臂 side
          <select v-model="form.side">
            <option value="left">左臂</option>
            <option value="right">右臂</option>
            <option value="both">both（仅草稿）</option>
            <option value="unknown">unknown（仅草稿）</option>
          </select>
        </label>
        <label>阶段 phase
          <select v-model="form.phase_code">
            <option v-for="p in profile?.phases" :key="p.code" :value="p.code">{{ p.display }}</option>
          </select>
        </label>
        <label>起点 (s)
          <input type="number" step="0.01" v-model.number="form.start_time_sec" />
        </label>
        <label>终点 (s)
          <input type="number" step="0.01" v-model.number="form.end_time_sec" />
        </label>
        <label>置信度 (0–1)
          <input type="number" step="0.05" min="0" max="1" v-model.number="form.confidence" />
        </label>
        <label class="note">备注
          <input v-model="form.note" />
        </label>
      </div>

      <div class="guidance" v-if="profile">
        <button type="button" @click="showGuidance = showGuidance ? null : form.phase_code">
          {{ phaseDisplayMap[form.phase_code] }} 标注判据
        </button>
        <div v-if="showGuidance && profile.boundary_definitions[boundaryNameFor(showGuidance)]" class="guidance-card">
          <p><strong>{{ profile.boundary_definitions[boundaryNameFor(showGuidance)].display }}</strong></p>
          <p>{{ profile.boundary_definitions[boundaryNameFor(showGuidance)].operational_definition }}</p>
          <p class="muted">参考关节：{{ profile.boundary_definitions[boundaryNameFor(showGuidance)].reference_joint }}</p>
          <p class="muted">{{ profile.boundary_definitions[boundaryNameFor(showGuidance)].annotation_guidance }}</p>
        </div>
      </div>

      <div class="actions">
        <button @click="submitForm">{{ editingSegmentId != null ? '保存修改' : '创建区间' }}</button>
        <button v-if="editingSegmentId != null" @click="resetForm">取消</button>
        <button v-if="editingSegmentId != null" class="danger" @click="removeSegment({ id: editingSegmentId } as any)">删除该区间</button>
      </div>
    </section>

    <section class="lifecycle" v-if="revision">
      <h3>生命周期</h3>
      <div v-if="!editable" class="locked-hint">
        当前 revision 非 draft（{{ revision.status }}），编辑已禁用。如需修改请点击「fork 新草稿」。
      </div>
      <div class="actions">
        <button v-if="editable" @click="runLifecycle('submit')">提交复核</button>
        <button v-if="revision.status === 'in_review'" @click="runLifecycle('pass')">复核通过</button>
        <button v-if="revision.status === 'in_review'" @click="runLifecycle('reject')">打回</button>
        <button v-if="revision.status === 'reviewed'" @click="runLifecycle('freeze')">冻结</button>
        <button @click="runLifecycle('fork')">fork 新草稿</button>
      </div>
      <p v-if="!editable && (form.side === 'both' || form.side === 'unknown')" class="warn">
        注意：提交复核前 side 必须收敛为 left / right，both / unknown 仅允许草稿。
      </p>
    </section>

    <p class="scope-note">
      本工作台仅用于人工参考标注。数据集导出、自动阶段识别、adjudication 等功能不在本版本实现。
    </p>
  </div>
</template>

<style scoped>
.labeling-view {
  padding: 16px;
  color: #e2e8f0;
}
.lv-head h2 {
  margin: 0 0 4px;
}
.meta {
  color: #94a3b8;
  font-size: 13px;
}
.error {
  color: #fca5a5;
  background: #3f1d1d;
  padding: 8px;
  border-radius: 6px;
}
.player {
  margin: 12px 0;
  display: flex;
  gap: 12px;
  align-items: center;
}
.timelines {
  margin: 12px 0;
}
.editor {
  border: 1px solid #2a3550;
  border-radius: 8px;
  padding: 12px;
  margin: 12px 0;
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.form-grid label {
  display: flex;
  flex-direction: column;
  font-size: 12px;
  color: #94a3b8;
}
.form-grid input,
.form-grid select {
  margin-top: 4px;
  padding: 6px;
  border-radius: 4px;
  border: 1px solid #334155;
  background: #0f172a;
  color: #e2e8f0;
}
.guidance {
  margin-top: 10px;
}
.guidance-card {
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 10px;
  margin-top: 6px;
}
.guidance-card .muted {
  color: #64748b;
  font-size: 12px;
}
.actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}
.actions button {
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid #334155;
  background: #1e293b;
  color: #e2e8f0;
  cursor: pointer;
}
.actions button.danger {
  background: #3f1d1d;
  border-color: #7f1d1d;
}
.locked-hint {
  color: #fbbf24;
  font-size: 13px;
}
.warn {
  color: #fbbf24;
  font-size: 12px;
}
.scope-note {
  color: #64748b;
  font-size: 12px;
  margin-top: 16px;
  border-top: 1px solid #1e293b;
  padding-top: 8px;
}
</style>
