<template>
  <div class="auth-page">
    <el-card class="auth-card auth-card-wide" shadow="never">
      <div class="auth-brand">
        <div class="brand-mark">泳</div>
        <div>
          <strong>智泳云枢</strong>
          <span>创建平台账号</span>
        </div>
      </div>
      <h1>注册</h1>
      <p>选择角色并创建账号。第一阶段重点支持教练业务闭环。</p>
      <el-form class="auth-form" label-position="top" :model="form" @submit.prevent="submit">
        <div class="form-grid">
          <el-form-item label="姓名" required>
            <el-input v-model="form.full_name" placeholder="例如：王教练" />
          </el-form-item>
          <el-form-item label="用户名" required>
            <el-input v-model="form.username" autocomplete="username" />
          </el-form-item>
          <el-form-item label="手机号">
            <el-input v-model="form.phone" />
          </el-form-item>
          <el-form-item label="邮箱">
            <el-input v-model="form.email" />
          </el-form-item>
          <el-form-item label="密码" required>
            <el-input v-model="form.password" autocomplete="new-password" show-password />
          </el-form-item>
          <el-form-item label="角色">
            <el-select v-model="form.role" class="full-select">
              <el-option label="教练" value="coach" />
              <el-option label="运动员" value="athlete" />
              <el-option label="管理员" value="admin" />
            </el-select>
          </el-form-item>
        </div>
        <div class="form-row">
          <span class="muted-text">已有账号</span>
          <el-button link type="primary" @click="$router.push('/login')">返回登录</el-button>
        </div>
        <el-button class="full-button" type="primary" native-type="submit" :loading="auth.loading" :disabled="!canSubmit">
          创建账号
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import type { UserRole } from '../types'

const auth = useAuthStore()
const router = useRouter()
const form = reactive({
  full_name: '',
  username: '',
  phone: '',
  email: '',
  password: '',
  role: 'coach' as UserRole
})

const canSubmit = computed(() => Boolean(form.full_name && form.username && form.password.length >= 6))

async function submit() {
  if (!canSubmit.value) return
  try {
    await auth.register({ ...form })
    ElMessage.success('注册成功')
    router.replace('/athletes')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '注册失败')
  }
}
</script>
