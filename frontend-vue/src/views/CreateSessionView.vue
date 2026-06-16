<template>
  <div>
    <div class="page-head">
      <div>
        <h1>创建测试任务</h1>
        <p>选择运动员并填写测试信息，创建后进入多机位视频上传。</p>
      </div>
      <el-button @click="$router.push('/athletes')">选择运动员</el-button>
    </div>

    <div class="grid-two">
      <el-form class="section" label-position="top" :model="form" @submit.prevent="submit">
        <el-form-item label="运动员" required>
          <el-select v-model="form.athlete_id" filterable class="full-select" placeholder="选择运动员">
            <el-option v-for="athlete in athletes" :key="athlete.id" :label="athlete.name" :value="athlete.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="测试标题" required>
          <el-input v-model="form.title" placeholder="例如：自由泳 50m 多机位测试" />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="测试日期">
            <el-date-picker v-model="form.session_date" class="full-select" type="date" value-format="YYYY-MM-DD" />
          </el-form-item>
          <el-form-item label="泳姿">
            <el-select v-model="form.stroke_type" class="full-select">
              <el-option label="自由泳" value="freestyle" />
              <el-option label="蛙泳" value="breaststroke" />
              <el-option label="仰泳" value="backstroke" />
              <el-option label="蝶泳" value="butterfly" />
            </el-select>
          </el-form-item>
          <el-form-item label="距离">
            <el-select v-model="form.distance_m" class="full-select">
              <el-option label="25m" :value="25" />
              <el-option label="50m" :value="50" />
              <el-option label="100m" :value="100" />
              <el-option label="200m" :value="200" />
            </el-select>
          </el-form-item>
          <el-form-item label="泳池长度">
            <el-select v-model="form.pool_length_m" class="full-select">
              <el-option label="25m" :value="25" />
              <el-option label="50m" :value="50" />
            </el-select>
          </el-form-item>
          <el-form-item label="场景">
            <el-select v-model="form.scene" class="full-select">
              <el-option label="训练" value="training" />
              <el-option label="比赛" value="competition" />
              <el-option label="课程" value="course" />
              <el-option label="康复" value="rehab" />
            </el-select>
          </el-form-item>
          <el-form-item label="场地">
            <el-input v-model="form.venue" />
          </el-form-item>
        </div>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="submitting" :disabled="!canSubmit">创建并上传视频</el-button>
      </el-form>

      <div class="section">
        <h2>测试任务链路</h2>
        <el-steps direction="vertical" :active="1">
          <el-step title="选择运动员" description="测试任务会绑定到运动员档案" />
          <el-step title="填写测试信息" description="泳姿、距离、泳池长度和训练场景" />
          <el-step title="多机位上传" description="侧面、正面、俯视、水下与半水下视频" />
          <el-step title="进入分析" description="提交后进入工作台与报告流程" />
        </el-steps>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createSession, listAthletes } from '../services/api'
import type { Athlete, CreateSessionForm } from '../types'

const route = useRoute()
const router = useRouter()
const athletes = ref<Athlete[]>([])
const submitting = ref(false)
const today = new Date().toISOString().slice(0, 10)
const form = reactive<CreateSessionForm>({
  athlete_id: route.query.athleteId ? Number(route.query.athleteId) : null,
  title: '',
  session_date: today,
  venue: '训练馆',
  stroke_type: 'freestyle',
  distance_m: 50,
  pool_length_m: 50,
  scene: 'training',
  notes: ''
})

const canSubmit = computed(() => Boolean(form.athlete_id && form.title))

async function loadAthletes() {
  athletes.value = await listAthletes()
  const selected = athletes.value.find((item) => item.id === form.athlete_id)
  if (selected && !form.title) {
    form.title = `${selected.name} ${strokeLabel(form.stroke_type)} ${form.distance_m}m 测试`
  }
}

async function submit() {
  if (!canSubmit.value) {
    ElMessage.warning('请选择运动员并填写测试标题')
    return
  }
  submitting.value = true
  try {
    const session = await createSession({ ...form })
    ElMessage.success('测试任务已创建')
    router.push(`/sessions/${session.id}/upload`)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '创建失败')
  } finally {
    submitting.value = false
  }
}

function strokeLabel(value: string) {
  return { freestyle: '自由泳', breaststroke: '蛙泳', backstroke: '仰泳', butterfly: '蝶泳', mixed: '混合' }[value] || value
}

onMounted(loadAthletes)
</script>
