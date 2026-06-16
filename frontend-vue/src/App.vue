<template>
  <el-container class="app-shell">
    <el-aside width="236px" class="side-nav">
      <div class="brand">
        <div class="brand-mark">泳</div>
        <div>
          <strong>智泳云枢</strong>
          <span>分析平台</span>
        </div>
      </div>
      <el-menu router :default-active="$route.path" class="nav-menu">
        <el-menu-item index="/upload">视频分析</el-menu-item>
        <el-menu-item index="/tasks">任务管理</el-menu-item>
      </el-menu>
      <div class="mode-badge">{{ demoMode ? 'Demo 数据模式' : '后端 API 模式' }}</div>
    </el-aside>
    <el-main class="main-panel">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { demoMode } from './services/api'
</script>
