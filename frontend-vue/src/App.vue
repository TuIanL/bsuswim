<template>
  <router-view v-if="isAuthRoute" />
  <el-container v-else class="app-shell">
    <el-aside width="236px" class="side-nav">
      <div class="brand">
        <div class="brand-mark">泳</div>
        <div>
          <strong>智泳云枢</strong>
          <span>分析平台</span>
        </div>
      </div>
      <el-menu router :default-active="$route.path" class="nav-menu">
        <el-menu-item index="/athletes">运动员</el-menu-item>
        <el-menu-item index="/sessions/new" :disabled="!auth.isCoach">创建测试</el-menu-item>
        <el-menu-item index="/tasks">测试任务</el-menu-item>
        <el-menu-item index="/workspace/1001">视觉工作台</el-menu-item>
        <el-menu-item index="/reports/1001">分析报告</el-menu-item>
      </el-menu>
      <div class="side-footer">
        <div class="mode-badge">{{ demoMode ? 'Demo 数据模式' : '后端 API 模式' }}</div>
        <div class="user-card">
          <strong>{{ auth.user?.full_name || auth.user?.username || 'Demo 用户' }}</strong>
          <span>{{ roleLabel }}</span>
        </div>
        <el-button class="logout-button" plain @click="logout">退出登录</el-button>
      </div>
    </el-aside>
    <el-main class="main-panel">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { demoMode } from './services/api'
import { useAuthStore } from './stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const isAuthRoute = computed(() => route.path === '/login' || route.path === '/register')
const roleLabel = computed(() => {
  if (auth.user?.role === 'admin') return '管理员'
  if (auth.user?.role === 'athlete') return '运动员'
  return '教练'
})

function logout() {
  auth.logout()
  router.push('/login')
}
</script>
