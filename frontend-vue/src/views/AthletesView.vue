<template>
  <div>
    <div class="page-head">
      <div>
        <h1>运动员管理</h1>
        <p>教练的核心入口：筛选运动员、查看档案，并快速创建测试任务。</p>
      </div>
      <el-button type="primary" :disabled="!auth.isCoach" @click="dialogOpen = true">新建运动员</el-button>
    </div>

    <div class="section">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" clearable placeholder="搜索姓名" />
        <el-select v-model="filters.stroke" clearable placeholder="泳姿">
          <el-option label="自由泳" value="freestyle" />
          <el-option label="蛙泳" value="breaststroke" />
          <el-option label="仰泳" value="backstroke" />
          <el-option label="蝶泳" value="butterfly" />
        </el-select>
        <el-select v-model="filters.team" clearable placeholder="队伍">
          <el-option v-for="team in teams" :key="team" :label="team" :value="team" />
        </el-select>
        <el-slider v-model="filters.scoreRange" range :min="0" :max="100" />
      </div>

      <el-table v-loading="loading" :data="filteredAthletes">
        <el-table-column prop="name" label="姓名" min-width="110" />
        <el-table-column label="性别" width="80">
          <template #default="{ row }">{{ genderLabel(row.gender) }}</template>
        </el-table-column>
        <el-table-column label="年龄" width="80">
          <template #default="{ row }">{{ calcAge(row.birth_date) || '-' }}</template>
        </el-table-column>
        <el-table-column label="主项" width="110">
          <template #default="{ row }">{{ strokeLabel(row.stroke_specialty) }}</template>
        </el-table-column>
        <el-table-column label="所属队伍" width="110">
          <template #default="{ row }">{{ row.team_name || teamLabel(row.team_id) }}</template>
        </el-table-column>
        <el-table-column label="最近测试" min-width="120">
          <template #default="{ row }">{{ row.recent_test_at || '-' }}</template>
        </el-table-column>
        <el-table-column label="技术评分" width="120">
          <template #default="{ row }">
            <el-tag :type="scoreType(row.current_score)">{{ row.current_score ?? '待测' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="$router.push(`/athletes/${row.id}`)">档案</el-button>
            <el-button size="small" type="primary" :disabled="!auth.isCoach" @click="createSession(row.id)">创建测试</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogOpen" title="新建运动员" width="560px">
      <el-form label-position="top" :model="newAthlete">
        <div class="form-grid">
          <el-form-item label="姓名" required>
            <el-input v-model="newAthlete.name" />
          </el-form-item>
          <el-form-item label="性别">
            <el-select v-model="newAthlete.gender" class="full-select">
              <el-option label="男" value="male" />
              <el-option label="女" value="female" />
            </el-select>
          </el-form-item>
          <el-form-item label="生日">
            <el-date-picker v-model="newAthlete.birth_date" class="full-select" type="date" value-format="YYYY-MM-DD" />
          </el-form-item>
          <el-form-item label="主项">
            <el-select v-model="newAthlete.stroke_specialty" class="full-select">
              <el-option label="自由泳" value="freestyle" />
              <el-option label="蛙泳" value="breaststroke" />
              <el-option label="仰泳" value="backstroke" />
              <el-option label="蝶泳" value="butterfly" />
            </el-select>
          </el-form-item>
          <el-form-item label="身高 cm">
            <el-input-number v-model="newAthlete.height_cm" class="full-select" :min="80" :max="230" />
          </el-form-item>
          <el-form-item label="体重 kg">
            <el-input-number v-model="newAthlete.weight_kg" class="full-select" :min="20" :max="150" />
          </el-form-item>
        </div>
        <el-form-item label="水平">
          <el-input v-model="newAthlete.level" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="newAthlete.notes" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" :disabled="!newAthlete.name" @click="saveAthlete">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createAthlete as createAthleteApi, listAthletes } from '../services/api'
import { useAuthStore } from '../stores/auth'
import type { Athlete, AthleteCreateInput } from '../types'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const saving = ref(false)
const dialogOpen = ref(false)
const athletes = ref<Athlete[]>([])
const filters = reactive({
  keyword: '',
  stroke: '',
  team: '',
  scoreRange: [0, 100]
})
const newAthlete = reactive<AthleteCreateInput>({
  name: '',
  gender: 'male',
  birth_date: '',
  stroke_specialty: 'freestyle',
  level: '',
  notes: ''
})

const teams = computed(() => Array.from(new Set(athletes.value.map((item) => item.team_name || teamLabel(item.team_id)).filter(Boolean))))
const filteredAthletes = computed(() => {
  const [min, max] = filters.scoreRange
  return athletes.value.filter((item) => {
    const score = item.current_score ?? 0
    return (
      (!filters.keyword || item.name.includes(filters.keyword)) &&
      (!filters.stroke || item.stroke_specialty === filters.stroke) &&
      (!filters.team || (item.team_name || teamLabel(item.team_id)) === filters.team) &&
      score >= min &&
      score <= max
    )
  })
})

async function load() {
  loading.value = true
  try {
    athletes.value = await listAthletes()
  } finally {
    loading.value = false
  }
}

async function saveAthlete() {
  saving.value = true
  try {
    await createAthleteApi({ ...newAthlete })
    ElMessage.success('运动员已创建')
    dialogOpen.value = false
    await load()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '创建失败')
  } finally {
    saving.value = false
  }
}

function createSession(athleteId: number) {
  router.push({ path: '/sessions/new', query: { athleteId } })
}

function calcAge(birthDate?: string | null) {
  if (!birthDate) return ''
  const birth = new Date(birthDate)
  if (Number.isNaN(birth.getTime())) return ''
  const today = new Date()
  let age = today.getFullYear() - birth.getFullYear()
  const monthDelta = today.getMonth() - birth.getMonth()
  if (monthDelta < 0 || (monthDelta === 0 && today.getDate() < birth.getDate())) age -= 1
  return age
}

function genderLabel(value?: string | null) {
  if (value === 'male') return '男'
  if (value === 'female') return '女'
  return value || '-'
}

function strokeLabel(value?: string | null) {
  return { freestyle: '自由泳', breaststroke: '蛙泳', backstroke: '仰泳', butterfly: '蝶泳', mixed: '混合' }[value || ''] || value || '-'
}

function teamLabel(teamId?: number | null) {
  if (!teamId) return '未分组'
  return `${teamId === 1 ? 'A' : teamId === 2 ? 'B' : teamId} 组`
}

function scoreType(score?: number | null) {
  if (!score) return 'info'
  if (score >= 80) return 'success'
  if (score >= 70) return 'warning'
  return 'danger'
}

onMounted(load)
</script>
