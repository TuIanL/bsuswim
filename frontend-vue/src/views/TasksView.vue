<template>
  <div>
    <div class="page-head">
      <div>
        <h1>任务管理</h1>
        <p>从后端恢复任务状态、进度、错误和后续操作。</p>
      </div>
      <el-button type="primary" @click="store.refresh()">刷新</el-button>
    </div>

    <el-table class="section" v-loading="store.loading" :data="store.tasks">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column label="训练" min-width="220">
        <template #default="{ row }">{{ row.session_metadata.session_title }}</template>
      </el-table-column>
      <el-table-column prop="stage" label="阶段" width="140" />
      <el-table-column label="状态" width="130">
        <template #default="{ row }">
          <el-tag :type="tagType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="进度" width="180">
        <template #default="{ row }">
          <el-progress :percentage="row.progress" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button size="small" @click="$router.push(`/workspace/${row.id}`)">工作台</el-button>
          <el-button size="small" :disabled="row.status !== 'completed'" @click="$router.push(`/reports/${row.id}`)">报告</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useTasksStore } from '../stores/tasks'
import type { TaskStatus } from '../types'

const store = useTasksStore()

function tagType(status: TaskStatus) {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'processing' || status === 'result_saving') return 'warning'
  return 'info'
}

onMounted(() => store.refresh())
</script>
