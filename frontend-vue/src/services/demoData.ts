import type { AnalysisTask, ReportData, WorkspaceData } from '../types'

export const demoTask: AnalysisTask = {
  id: 1001,
  video_id: 9001,
  status: 'completed',
  progress: 100,
  stage: 'completed',
  session_metadata: {
    session_title: '自由泳侧拍技术评估',
    venue: '训练馆 50m 池',
    swimmer_label: 'A 组运动员',
    stroke_type: 'freestyle',
    level: 'competitive',
    capture_mode: 'side_view'
  },
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  completed_at: new Date().toISOString(),
  actions: ['workspace', 'report']
}

export const demoWorkspace: WorkspaceData = {
  task: demoTask,
  result: {
    id: 1,
    task_id: demoTask.id,
    schema_version: 'swim-analysis.v1',
    detections: [
      { time: 0, bbox: [0.18, 0.36, 0.34, 0.18], label: 'swimmer', confidence: 0.93 },
      { time: 1.5, bbox: [0.3, 0.34, 0.35, 0.2], label: 'swimmer', confidence: 0.91 }
    ],
    keypoint_frames: [
      {
        time: 0,
        points: [
          { name: 'head', x: 0.28, y: 0.39 },
          { name: 'shoulder', x: 0.36, y: 0.43 },
          { name: 'hip', x: 0.48, y: 0.48 },
          { name: 'knee', x: 0.6, y: 0.5 }
        ]
      }
    ],
    phases: [
      { start: 0, end: 1.2, label: '入水与前伸' },
      { start: 1.2, end: 2.6, label: '抱水与推水' }
    ],
    metrics: {
      overall_score: 81,
      body_line_score: 78,
      rhythm_score: 83,
      symmetry_score: 74,
      kick_score: 76
    },
    diagnostics: [
      {
        title: '身体中线轻微摆动',
        severity: 'medium',
        evidence: '髋部关键点在推水阶段出现横向波动',
        suggestion: '增加侧身打腿和单臂划水练习'
      }
    ],
    created_at: new Date().toISOString()
  }
}

export const demoReport: ReportData = {
  task_id: demoTask.id,
  source: 'demo',
  generated_at: new Date().toISOString(),
  report: {
    summary: {
      title: '自由泳侧拍技术评估',
      stroke_type: 'freestyle',
      overall_score: 81,
      headline: 'demo 数据，用于无后端环境展示'
    },
    metrics: demoWorkspace.result?.metrics,
    diagnostics: demoWorkspace.result?.diagnostics,
    recommendations: [
      { title: '保持身体中线稳定', target: '降低左右摆动，提高划水效率', linked_issue: 'body_line' }
    ],
    charts: {
      radar: [
        { name: '身体线', value: 78 },
        { name: '节奏', value: 83 },
        { name: '对称性', value: 74 },
        { name: '打腿', value: 76 }
      ]
    },
    provenance: {
      source: 'demo',
      schema_version: 'swim-analysis.v1'
    }
  }
}
