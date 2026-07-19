<template>
  <div class="module-grid">
    <div v-for="key in moduleKeys" :key="key" class="module-card" :class="statusClass(readiness[key])">
      <div class="module-head">
        <span class="module-name">{{ MODULE_LABELS[key] }}</span>
        <el-tag :type="moduleStatusType(readiness[key])" size="small">{{ MODULE_STATUS_LABELS[readiness[key]] }}</el-tag>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { KinematicsModuleKey, KinematicsModuleReadiness, ModuleReadinessStatus } from '../../types'
import { MODULE_LABELS, MODULE_STATUS_LABELS, moduleStatusType } from '../../utils/kinematicsWorkflow'

const props = defineProps<{ readiness?: Partial<KinematicsModuleReadiness> | null }>()

const moduleKeys: KinematicsModuleKey[] = ['body_posture', 'upper_limb', 'lower_limb', 'head_trunk']

const readiness = computed<Record<KinematicsModuleKey, ModuleReadinessStatus>>(() => {
  const r = props.readiness ?? {}
  return {
    body_posture: r.body_posture ?? 'blocked',
    upper_limb: r.upper_limb ?? 'blocked',
    lower_limb: r.lower_limb ?? 'blocked',
    head_trunk: r.head_trunk ?? 'degraded'
  }
})

function statusClass(s: ModuleReadinessStatus) {
  return `module-${s}`
}
</script>

<style scoped>
.module-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 8px; }
.module-card { border: 1px solid #ebeef5; border-radius: 8px; padding: 12px; }
.module-head { display: flex; align-items: center; justify-content: space-between; }
.module-name { font-weight: 500; font-size: 14px; }
.module-ready { border-color: #e1f3d8; }
.module-degraded { border-color: #faecd8; }
.module-blocked { border-color: #fde2e2; }
</style>
