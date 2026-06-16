<template>
  <div>
    <div class="page-head">
      <div>
        <h1>视频分析</h1>
        <p>上传训练视频并创建真实后端分析任务；未配置 API 时会使用 demo 数据。</p>
      </div>
      <el-button type="primary" @click="$router.push('/tasks')">任务管理</el-button>
    </div>

    <div class="grid-two">
      <el-form ref="formRef" class="section" :model="form" label-position="top">
        <el-form-item label="训练视频">
          <el-upload
            drag
            :auto-upload="false"
            :limit="1"
            accept="video/*"
            :on-change="handleFileChange"
          >
            <div>拖入视频或点击选择</div>
            <small>支持浏览器可识别的视频格式</small>
          </el-upload>
        </el-form-item>
        <el-form-item label="训练标题" required>
          <el-input v-model="form.session_title" placeholder="例如：自由泳侧拍技术评估" />
        </el-form-item>
        <el-form-item label="泳姿">
          <el-select v-model="form.stroke_type">
            <el-option label="自由泳" value="freestyle" />
            <el-option label="蛙泳" value="breaststroke" />
            <el-option label="仰泳" value="backstroke" />
            <el-option label="蝶泳" value="butterfly" />
          </el-select>
        </el-form-item>
        <el-form-item label="训练场地">
          <el-input v-model="form.venue" />
        </el-form-item>
        <el-form-item label="运动员">
          <el-input v-model="form.swimmer_label" />
        </el-form-item>
        <el-form-item label="采集方式">
          <el-radio-group v-model="form.capture_mode">
            <el-radio-button label="side_view">侧拍</el-radio-button>
            <el-radio-button label="underwater">水下</el-radio-button>
            <el-radio-button label="mixed">混合</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-button type="primary" :loading="submitting" :disabled="!canSubmit" @click="submit">开始分析</el-button>
      </el-form>

      <div class="section">
        <h2>分析链路</h2>
        <el-steps direction="vertical" :active="1">
          <el-step title="上传视频" description="保存到本地 uploads，并记录文件元数据" />
          <el-step title="创建任务" description="状态入库，可刷新恢复" />
          <el-step title="模型服务" description="独立 FastAPI 服务执行 YOLO 类分析" />
          <el-step title="工作台与报告" description="Canvas 叠加与 HTML 报告展示" />
        </el-steps>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { UploadFile } from 'element-plus'
import { ElMessage } from 'element-plus'
import { createAnalysisTask, uploadVideo } from '../services/api'

const router = useRouter()
const selectedFile = ref<File | null>(null)
const submitting = ref(false)
const form = reactive({
  session_title: '',
  venue: '',
  session_date: '',
  swimmer_label: '',
  stroke_type: 'freestyle',
  level: 'competitive',
  capture_mode: 'side_view'
})

const canSubmit = computed(() => Boolean(form.session_title && selectedFile.value))

function handleFileChange(file: UploadFile) {
  selectedFile.value = file.raw || null
}

async function submit() {
  if (!selectedFile.value) return
  submitting.value = true
  try {
    const video = await uploadVideo(selectedFile.value)
    const task = await createAnalysisTask(video.id, { ...form })
    ElMessage.success('分析任务已创建')
    router.push('/tasks')
    setTimeout(() => router.push(`/workspace/${task.id}`), 300)
  } finally {
    submitting.value = false
  }
}
</script>
