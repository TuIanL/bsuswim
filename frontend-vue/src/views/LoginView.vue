<template>
  <div class="auth-page">
    <el-card class="auth-card" shadow="never">
      <div class="auth-brand">
        <div class="brand-mark">泳</div>
        <div>
          <strong>智泳云枢</strong>
          <span>教练业务平台</span>
        </div>
      </div>
      <h1>登录</h1>
      <p>进入运动员档案、测试任务和多机位视频上传流程。</p>
      <el-form class="auth-form" label-position="top" :model="form" @submit.prevent="submit">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" autocomplete="username" placeholder="coach_demo" />
        </el-form-item>
        <el-form-item label="密码" required>
          <el-input v-model="form.password" autocomplete="current-password" placeholder="请输入密码" show-password />
        </el-form-item>
        <div class="form-row">
          <el-checkbox v-model="form.remember">记住登录状态</el-checkbox>
          <el-button link type="primary" @click="$router.push('/register')">注册账号</el-button>
        </div>
        <el-button class="full-button" type="primary" native-type="submit" :loading="auth.loading" :disabled="!canSubmit">
          登录
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const form = reactive({
  username: '',
  password: '',
  remember: true
})

const canSubmit = computed(() => Boolean(form.username && form.password))

async function submit() {
  if (!canSubmit.value) return
  try {
    await auth.login(form)
    ElMessage.success('登录成功')
    router.replace((route.query.redirect as string) || '/athletes')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '登录失败')
  }
}
</script>
