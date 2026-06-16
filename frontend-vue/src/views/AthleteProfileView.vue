<template>
  <div>
    <div class="page-head">
      <div>
        <h1>{{ athlete?.name || '运动员档案' }}</h1>
        <p>基础资料、历史测试、最近评分和长期趋势的入口页。</p>
      </div>
      <div class="action-row">
        <el-button @click="$router.push('/athletes')">返回列表</el-button>
        <el-button type="primary" :disabled="!auth.isCoach || !athlete" @click="createSession">创建新测试</el-button>
      </div>
    </div>

    <div v-if="loading" class="section">加载中...</div>
    <el-empty v-else-if="!athlete" class="section" description="未找到运动员" />
    <template v-else>
      <div class="grid-two">
        <div class="section">
          <h2>基础信息</h2>
          <div class="info-grid">
            <div class="info-item"><span>性别</span><strong>{{ genderLabel(athlete.gender) }}</strong></div>
            <div class="info-item"><span>年龄</span><strong>{{ calcAge(athlete.birth_date) || '-' }}</strong></div>
            <div class="info-item"><span>主项</span><strong>{{ strokeLabel(athlete.stroke_specialty) }}</strong></div>
            <div class="info-item"><span>队伍</span><strong>{{ athlete.team_name || teamLabel(athlete.team_id) }}</strong></div>
            <div class="info-item"><span>身高</span><strong>{{ athlete.height_cm ? `${athlete.height_cm} cm` : '-' }}</strong></div>
            <div class="info-item"><span>体重</span><strong>{{ athlete.weight_kg ? `${athlete.weight_kg} kg` : '-' }}</strong></div>
          </div>
          <p class="muted-text profile-note">{{ athlete.notes || '暂无备注' }}</p>
        </div>
        <div class="section">
          <h2>最近技术评分</h2>
          <div class="score-large">{{ latestScore }}</div>
          <p class="muted-text">最近测试：{{ athlete.recent_test_at || latestSession?.session_date || '暂无' }}</p>
        </div>
      </div>

      <div class="section">
        <h2>核心指标趋势</h2>
        <div ref="chartRef" style="height: 300px" />
      </div>

      <div class="section">
        <div class="page-head compact-head">
          <div>
            <h2>历史测试记录</h2>
            <p>测试日期、泳姿、距离、状态和后续操作。</p>
          </div>
        </div>
        <el-table v-if="sessions.length" :data="sessions">
          <el-table-column prop="session_date" label="测试日期" width="130" />
          <el-table-column prop="title" label="测试任务" min-width="200" />
          <el-table-column label="泳姿" width="110">
            <template #default="{ row }">{{ strokeLabel(row.stroke_type) }}</template>
          </el-table-column>
          <el-table-column label="距离" width="90">
            <template #default="{ row }">{{ row.distance_m ? `${row.distance_m}m` : '-' }}</template>
          </el-table-column>
          <el-table-column label="评分" width="90">
            <template #default="{ row }">{{ row.score ?? '-' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="120">
            <template #default="{ row }"><el-tag>{{ statusLabel(row.status) }}</el-tag></template>
          </el-table-column>
          <el-table-column label="操作" width="210">
            <template #default="{ row }">
              <el-button size="small" @click="$router.push(`/sessions/${row.id}/upload`)">上传</el-button>
              <el-button size="small" :disabled="row.status !== 'completed'" @click="$router.push('/reports/1001')">报告</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="暂无历史测试">
          <el-button type="primary" :disabled="!auth.isCoach" @click="createSession">创建新测试</el-button>
        </el-empty>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import * as echarts from 'echarts'
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getAthlete, getAthleteTrend, listAthleteSessions } from '../services/api'
import { useAuthStore } from '../stores/auth'
import type { Athlete, AthleteTrendPoint, TrainingSession } from '../types'

const props = defineProps<{ athleteId: string }>()
const router = useRouter()
const auth = useAuthStore()
const athlete = ref<Athlete | null>(null)
const sessions = ref<TrainingSession[]>([])
const trends = ref<AthleteTrendPoint[]>([])
const loading = ref(true)
const chartRef = ref<HTMLDivElement | null>(null)

const latestSession = computed(() => sessions.value[0])
const latestScore = computed(() => athlete.value?.current_score ?? latestSession.value?.score ?? '待测')

async function load() {
  loading.value = true
  const athleteId = Number(props.athleteId)
  try {
    const [athleteData, sessionData, trendData] = await Promise.all([
      getAthlete(athleteId),
      listAthleteSessions(athleteId),
      getAthleteTrend(athleteId)
    ])
    athlete.value = athleteData
    sessions.value = sessionData
    trends.value = trendData
    await nextTick()
    renderChart()
  } finally {
    loading.value = false
  }
}

function renderChart() {
  if (!chartRef.value) return
  const chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['技术评分', '身体水平度', '划频', '划幅'], bottom: 0 },
    grid: { left: 34, right: 18, top: 24, bottom: 58 },
    xAxis: { type: 'category', data: trends.value.map((item) => item.date) },
    yAxis: { type: 'value', min: 0, max: 100 },
    series: [
      { name: '技术评分', type: 'line', smooth: true, data: trends.value.map((item) => item.score) },
      { name: '身体水平度', type: 'line', smooth: true, data: trends.value.map((item) => item.body_line) },
      { name: '划频', type: 'line', smooth: true, data: trends.value.map((item) => item.stroke_rate) },
      { name: '划幅', type: 'line', smooth: true, data: trends.value.map((item) => item.stroke_length) }
    ]
  })
}

function createSession() {
  if (!athlete.value) return
  router.push({ path: '/sessions/new', query: { athleteId: athlete.value.id } })
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

function statusLabel(value: string) {
  return { draft: '待上传', video_uploaded: '已上传', analyzing: '分析中', completed: '已完成', failed: '失败' }[value] || value
}

onMounted(load)
</script>
