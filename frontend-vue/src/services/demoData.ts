import type {
  AnalysisTask,
  Athlete,
  AthleteTrendPoint,
  ReportData,
  SessionVideo,
  TrainingSession,
  User,
  VideoFile,
  WorkspaceData
} from '../types'

const now = new Date().toISOString()

export const demoUser: User = {
  id: 1,
  username: 'coach_demo',
  email: 'coach@example.com',
  phone: '13800000000',
  full_name: '示例教练',
  role: 'coach',
  is_active: true,
  created_at: now,
  updated_at: now
}

export const demoAthletes: Athlete[] = [
  {
    id: 101,
    name: '林澈',
    gender: 'male',
    birth_date: '2008-04-12',
    height_cm: 178,
    weight_kg: 67,
    stroke_specialty: 'freestyle',
    level: '专项提高',
    coach_id: demoUser.id,
    team_id: 1,
    team_name: 'A 组',
    notes: '自由泳主项，重点改善身体水平度。',
    current_score: 82,
    recent_test_at: '2026-06-12',
    created_at: now,
    updated_at: now
  },
  {
    id: 102,
    name: '周雨桐',
    gender: 'female',
    birth_date: '2009-09-03',
    height_cm: 169,
    weight_kg: 56,
    stroke_specialty: 'backstroke',
    level: '校队',
    coach_id: demoUser.id,
    team_id: 2,
    team_name: 'B 组',
    notes: '仰泳节奏稳定，入水角度待优化。',
    current_score: 76,
    recent_test_at: '2026-06-08',
    created_at: now,
    updated_at: now
  },
  {
    id: 103,
    name: '陈一诺',
    gender: 'female',
    birth_date: '2010-01-21',
    height_cm: 164,
    weight_kg: 51,
    stroke_specialty: 'butterfly',
    level: '青训',
    coach_id: demoUser.id,
    team_id: 1,
    team_name: 'A 组',
    notes: '蝶泳核心力量提升阶段。',
    current_score: 71,
    recent_test_at: '2026-05-30',
    created_at: now,
    updated_at: now
  }
]

export const demoSessions: TrainingSession[] = [
  {
    id: 201,
    athlete_id: 101,
    coach_id: demoUser.id,
    title: '自由泳 50m 侧面与水下联测',
    session_date: '2026-06-12',
    venue: '训练馆 50m 池',
    stroke_type: 'freestyle',
    distance_m: 50,
    pool_length_m: 50,
    scene: 'training',
    status: 'completed',
    notes: '重点观察推水阶段髋部稳定性。',
    score: 82,
    created_at: now,
    updated_at: now
  },
  {
    id: 202,
    athlete_id: 102,
    coach_id: demoUser.id,
    title: '仰泳 25m 节奏复测',
    session_date: '2026-06-08',
    venue: '训练馆 25m 池',
    stroke_type: 'backstroke',
    distance_m: 25,
    pool_length_m: 25,
    scene: 'training',
    status: 'video_uploaded',
    notes: '观察划频变化。',
    score: 76,
    created_at: now,
    updated_at: now
  }
]

export const demoSessionVideos: SessionVideo[] = [
  {
    id: 301,
    session_id: 201,
    video_file_id: 9001,
    view_type: 'side',
    fps: 60,
    resolution: '1920x1080',
    sync_offset_ms: 0,
    created_at: now,
    upload_status: 'success',
    video: {
      id: 9001,
      original_filename: 'demo-side-view-freestyle.mp4',
      stored_filename: 'demo-side-view-freestyle.mp4',
      storage_path: 'demo-side-view-freestyle.mp4',
      mime_type: 'video/mp4',
      size_bytes: 42 * 1024 * 1024,
      checksum_sha256: 'demo',
      created_at: now,
      playback_url: ''
    }
  },
  {
    id: 302,
    session_id: 201,
    video_file_id: 9002,
    view_type: 'underwater',
    fps: 60,
    resolution: '1920x1080',
    sync_offset_ms: 120,
    created_at: now,
    upload_status: 'success',
    video: {
      id: 9002,
      original_filename: 'demo-underwater-freestyle.mp4',
      stored_filename: 'demo-underwater-freestyle.mp4',
      storage_path: 'demo-underwater-freestyle.mp4',
      mime_type: 'video/mp4',
      size_bytes: 38 * 1024 * 1024,
      checksum_sha256: 'demo',
      created_at: now,
      playback_url: ''
    }
  }
]

export const demoAthleteTrends: Record<number, AthleteTrendPoint[]> = {
  101: [
    { date: '2026-04-18', score: 74, body_line: 70, stroke_rate: 78, stroke_length: 72, swolf: 68 },
    { date: '2026-05-16', score: 78, body_line: 75, stroke_rate: 80, stroke_length: 76, swolf: 72 },
    { date: '2026-06-12', score: 82, body_line: 81, stroke_rate: 83, stroke_length: 79, swolf: 76 }
  ],
  102: [
    { date: '2026-04-22', score: 69, body_line: 73, stroke_rate: 67, stroke_length: 70, swolf: 65 },
    { date: '2026-05-20', score: 73, body_line: 76, stroke_rate: 72, stroke_length: 74, swolf: 68 },
    { date: '2026-06-08', score: 76, body_line: 78, stroke_rate: 75, stroke_length: 76, swolf: 71 }
  ],
  103: [
    { date: '2026-04-08', score: 64, body_line: 62, stroke_rate: 68, stroke_length: 61, swolf: 60 },
    { date: '2026-05-05', score: 68, body_line: 66, stroke_rate: 71, stroke_length: 65, swolf: 63 },
    { date: '2026-05-30', score: 71, body_line: 70, stroke_rate: 73, stroke_length: 68, swolf: 66 }
  ]
}

export const demoTask: AnalysisTask = {
  id: 1001,
  session_id: 201,
  video_id: 9001,
  status: 'completed',
  progress: 100,
  stage: 'completed',
  pipeline_type: 'model_service',
  pipeline_version: 'model_service_v1',
  attempt_count: 1,
  failed_stage: null,
  error_code: null,
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
  session_id: demoTask.session_id,
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

let athletes = [...demoAthletes]
let sessions = [...demoSessions]
let sessionVideos = [...demoSessionVideos]
let tasks = [demoTask]
let videoSequence = 9100
let athleteSequence = 200
let sessionSequence = 300
let sessionVideoSequence = 400
let taskSequence = 1001

export function resetDemoBusinessData() {
  athletes = [...demoAthletes]
  sessions = [...demoSessions]
  sessionVideos = [...demoSessionVideos]
  tasks = [demoTask]
}

export function getDemoAthletes() {
  return [...athletes]
}

export function createDemoAthlete(input: Partial<Athlete>) {
  const athlete: Athlete = {
    id: ++athleteSequence,
    name: input.name || '新运动员',
    gender: input.gender || 'male',
    birth_date: input.birth_date || null,
    height_cm: input.height_cm ?? null,
    weight_kg: input.weight_kg ?? null,
    stroke_specialty: input.stroke_specialty || 'freestyle',
    level: input.level || '待分级',
    coach_id: demoUser.id,
    team_id: input.team_id ?? null,
    team_name: input.team_name || '未分组',
    notes: input.notes || null,
    current_score: null,
    recent_test_at: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  }
  athletes = [athlete, ...athletes]
  return athlete
}

export function getDemoAthlete(id: number) {
  return athletes.find((athlete) => athlete.id === id) || null
}

export function getDemoAthleteSessions(athleteId: number) {
  return sessions.filter((session) => session.athlete_id === athleteId)
}

export function getDemoAthleteTrend(athleteId: number) {
  return demoAthleteTrends[athleteId] || []
}

export function getDemoSessions() {
  return [...sessions].sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))
}

export function getDemoSession(id: number) {
  return sessions.find((session) => session.id === id) || null
}

export function createDemoSession(input: Partial<TrainingSession>) {
  const createdAt = new Date().toISOString()
  const session: TrainingSession = {
    id: ++sessionSequence,
    athlete_id: Number(input.athlete_id),
    coach_id: demoUser.id,
    title: input.title || '新建测试任务',
    session_date: input.session_date || createdAt.slice(0, 10),
    venue: input.venue || '训练馆',
    stroke_type: input.stroke_type || 'freestyle',
    distance_m: input.distance_m ?? 50,
    pool_length_m: input.pool_length_m ?? 50,
    scene: input.scene || 'training',
    status: 'draft',
    notes: input.notes || null,
    score: null,
    created_at: createdAt,
    updated_at: createdAt
  }
  sessions = [session, ...sessions]
  return session
}

export function createDemoVideo(file: File): VideoFile {
  return {
    id: ++videoSequence,
    original_filename: file.name,
    stored_filename: file.name,
    storage_path: file.name,
    mime_type: file.type,
    size_bytes: file.size,
    checksum_sha256: 'demo',
    created_at: new Date().toISOString(),
    playback_url: ''
  }
}

export function bindDemoSessionVideo(
  sessionId: number,
  video: VideoFile,
  input: { view_type: SessionVideo['view_type']; fps?: number | null; resolution?: string | null; sync_offset_ms: number }
) {
  const link: SessionVideo = {
    id: ++sessionVideoSequence,
    session_id: sessionId,
    video_file_id: video.id,
    view_type: input.view_type,
    fps: input.fps ?? null,
    resolution: input.resolution ?? null,
    sync_offset_ms: input.sync_offset_ms,
    created_at: new Date().toISOString(),
    upload_status: 'success',
    video
  }
  sessionVideos = [link, ...sessionVideos.filter((item) => !(item.session_id === sessionId && item.view_type === input.view_type))]
  sessions = sessions.map((session) =>
    session.id === sessionId ? { ...session, status: 'video_uploaded', updated_at: new Date().toISOString() } : session
  )
  return link
}

export function getDemoSessionVideos(sessionId: number) {
  return sessionVideos.filter((item) => item.session_id === sessionId)
}

export function submitDemoAnalysis(sessionId: number) {
  const session = getDemoSession(sessionId)
  const createdAt = new Date().toISOString()
  const task: AnalysisTask = {
    ...demoTask,
    id: ++taskSequence,
    session_id: sessionId,
    status: 'completed',
    progress: 100,
    stage: 'completed',
    created_at: createdAt,
    updated_at: createdAt,
    completed_at: createdAt,
    request_payload: {
      schema_version: 'analysis.request.v1',
      session_id: sessionId,
      session: session ? { id: session.id, title: session.title, stroke_type: session.stroke_type } : null,
      videos: getDemoSessionVideos(sessionId)
    },
    session_metadata: {
      session_title: session?.title || demoTask.session_metadata?.session_title || 'Demo 游泳分析',
      venue: session?.venue || '',
      session_date: session?.session_date || '',
      stroke_type: session?.stroke_type || 'freestyle',
      capture_mode: 'multi_camera'
    }
  }
  tasks = [task, ...tasks.filter((item) => item.session_id !== sessionId)]
  sessions = sessions.map((item) =>
    item.id === sessionId ? { ...item, status: 'completed', score: 81, updated_at: createdAt } : item
  )
  return task
}

export function getDemoTasks() {
  return [...tasks].sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))
}

export function getDemoTask(taskId: number) {
  return tasks.find((task) => task.id === taskId) || demoTask
}

export function getDemoWorkspace(taskId: number): WorkspaceData {
  const task = getDemoTask(taskId)
  return {
    ...demoWorkspace,
    task,
    videos: getDemoSessionVideos(task.session_id).map((item) => item.video),
    session_videos: getDemoSessionVideos(task.session_id)
  }
}

export const swimReportV1DemoReport: ReportData = {
  session_id: demoTask.session_id,
  task_id: demoTask.id,
  source: 'demo',
  generated_at: new Date().toISOString(),
  report: {
    schema_version: 'swim-report.v1',
    report_mode: 'side_technical',
    title: '自由泳侧面技术分析报告',
    summary: {
      title: '自由泳侧面技术分析报告',
      overall_score: 82,
      overall_level: '良好',
      overall_conclusion: '身体位置随速度提升改善，但高肘抱水和推进效率仍需重点优化。',
      main_strengths: ['高速阶段身体位置改善明显', '腿部髋膝角度整体稳定'],
      main_limitations: ['高肘抱水不足', '低速阶段身体支撑不足', '速度提升主要依赖划频增加'],
      top_findings: [
        { title: '低速阶段身体与水平面夹角较大', severity: 'high' },
        { title: '高肘抱水不足贯穿全速度区间', severity: 'high' },
        { title: '速度提升主要依赖划频增加', severity: 'medium' },
      ],
      top_recommendations: ['进行高肘抱水专项训练', '加强低速阶段核心控制'],
    },
    sections: [
      {
        key: 'overview',
        type: 'overview',
        title: '测试概况',
        summary: '本报告基于侧面自由泳视频与 Kinovea 标注结果，评估身体位置、上肢抱水、腿部技术与推进效率。',
        metrics: [
          { key: 'body_angle_deg', label: '身体水平角', value: 12.4, unit: '°' },
          { key: 'stroke_rate_spm', label: '平均划频', value: 64.8, unit: 'spm' },
          { key: 'elbow_angle_deg', label: '抱水肘角', value: 154, unit: '°' },
        ],
        findings: [
          { content: '本次分析识别出 3 个主要技术问题，其中高严重度问题 2 个。', severity: 'high' },
        ],
      },
      {
        key: 'body_position',
        title: '身体位置与流线型效率分析',
        summary: '身体位置随速度提升逐步改善，低速阶段身体支撑不足。',
        metrics: [
          { key: 'body_angle_deg', label: '平均身体水平角', value: 12.4, unit: '°' },
          { key: 'body_angle_deg_low_speed', label: '低速阶段', value: 14, unit: '°' },
          { key: 'body_angle_deg_high_speed', label: '高速阶段', value: 7, unit: '°' },
        ],
        assets: [
          {
            key: 'body_low_speed',
            type: 'annotated_frame' as const,
            label: '低速阶段',
            value: '0.91 m/s',
            caption: '身体与水平面夹角 14°',
            status: 'poor' as const,
          },
          {
            key: 'body_mid_speed',
            type: 'annotated_frame' as const,
            label: '中速阶段',
            value: '1.28 m/s',
            caption: '身体与水平面夹角 12°',
            status: 'warning' as const,
          },
          {
            key: 'body_high_speed',
            type: 'annotated_frame' as const,
            label: '高速阶段',
            value: '1.45 m/s',
            caption: '身体与水平面夹角 7°',
            status: 'good' as const,
          },
        ],
        findings: [
          { title: '身体位置随速度提升而改善', content: '低速 14° → 高速 7°，流线型效率明显提升。', severity: 'medium' as const },
          { title: '低速阶段身体支撑不足', content: '二次腿阶段更容易出现中段下沉。', severity: 'high' as const },
        ],
        recommendations: [
          { content: '加强低速阶段核心支撑与身体水平控制训练。', category: 'technical' },
          { content: '强化二次腿配合下的髋部支撑能力。', category: 'rhythm' },
        ],
      },
      {
        key: 'catch_pull',
        title: '上肢抱水与推进效率分析',
        summary: '高肘抱水不足，速度提升主要依赖划频增加，划幅下降。',
        metrics: [
          { key: 'elbow_angle_deg', label: '抱水肘角', value: 154, unit: '°' },
          { key: 'stroke_rate_change_pct', label: '划频提升', value: 90.3, unit: '%' },
          { key: 'stroke_length_change_pct', label: '划幅变化', value: -16.5, unit: '%' },
        ],
        assets: [
          {
            key: 'catch_low_speed',
            type: 'annotated_frame' as const,
            label: '抱水阶段',
            caption: '高肘不足，前臂迎水面积受限',
            status: 'poor' as const,
          },
          {
            key: 'catch_high_speed',
            type: 'annotated_frame' as const,
            label: '高速抱水',
            caption: '肘角偏大，支撑不足',
            status: 'warning' as const,
          },
        ],
        charts: [
          {
            key: 'stroke_rate_trend',
            type: 'line' as const,
            title: '划频变化趋势',
            x_axis: ['1', '2', '3', '4', '5', '6', '7'],
            series: [
              { name: '划频', data: [0.72, 0.84, 0.91, 0.99, 1.08, 1.19, 1.37], unit: 'Hz' },
            ],
          },
          {
            key: 'stroke_length_trend',
            type: 'line' as const,
            title: '划幅变化趋势',
            x_axis: ['1', '2', '3', '4', '5', '6', '7'],
            series: [
              { name: '划幅', data: [1.27, 1.27, 1.24, 1.23, 1.18, 1.14, 1.06], unit: 'm/次' },
            ],
          },
        ],
        findings: [
          { title: '高肘抱水不足贯穿全速度区间', content: '低速阶段已经存在，高速阶段仍未改善。', severity: 'high' as const },
          { title: '速度提升主要依赖划频代偿', content: '划频 +90.3%，划幅 -16.5%。', severity: 'medium' as const },
        ],
        recommendations: [
          { content: '进行高肘抱水专项、单臂划水训练。', category: 'technical' },
          { content: '优化划频—划幅协调，避免单纯依赖高划频。', category: 'rhythm' },
        ],
      },
      {
        key: 'leg_kick',
        title: '腿部技术角度分析',
        summary: '腿部技术整体表现较稳定，低速阶段膝角控制仍需优化。',
        metrics: [
          { key: 'knee_angle_deg', label: '平均膝关节角', value: 125, unit: '°' },
          { key: 'ankle_extension_angle_deg', label: '踝伸展角', value: 45, unit: '°' },
        ],
        findings: [
          { title: '髋膝角度整体稳定', content: '随着速度提升，膝关节角度保持在合理范围。', severity: 'low' as const },
        ],
        recommendations: [
          { content: '踝关节柔韧性训练，提升脚踝伸展能力。', category: 'mobility' },
        ],
      },
      {
        key: 'efficiency',
        title: '专项技术效率分析',
        summary: '游进效率受推进效率不足影响，SWOLF 偏高。',
        metrics: [
          { key: 'speed_mps', label: '平均速度', value: 1.45, unit: 'm/s' },
          { key: 'stroke_rate_spm', label: '平均划频', value: 64.8, unit: 'spm' },
          { key: 'stroke_length_m', label: '平均划幅', value: 1.06, unit: 'm' },
        ],
        charts: [
          {
            key: 'speed_trend',
            type: 'line' as const,
            title: '速度变化',
            x_axis: ['1', '2', '3', '4', '5', '6', '7'],
            series: [
              { name: '速度', data: [0.91, 1.06, 1.13, 1.21, 1.28, 1.34, 1.45], unit: 'm/s' },
            ],
          },
        ],
        findings: [
          { content: '速度提升过程中划频增加但划幅下降，提示推进效率有提升空间。', severity: 'medium' as const },
        ],
        recommendations: [
          { content: '通过高肘抱水专项训练提升单次划水推进距离。', category: 'technical' },
          { content: '复测目标：划幅下降幅度控制在 10% 以内。', category: 'retest' },
        ],
      },
      {
        key: 'recommendations',
        type: 'recommendation' as const,
        title: '训练建议与复测目标',
        summary: '建议围绕身体支撑、高肘抱水和推进效率进行 3–4 周训练后复测。',
        recommendations: [
          { content: '高肘抱水专项训练', category: 'technical' },
          { content: '上肢力量提升训练', category: 'strength' },
          { content: '身体水平角控制在 10° 以内', category: 'retest' },
          { content: '划幅下降幅度控制在 10% 以内', category: 'retest' },
        ],
      },
    ],
    provenance: {
      source: 'demo',
      schema_version: 'swim-report.v1',
    },
  },
}

export function getDemoReport(
  sessionId: number,
  format?: 'legacy' | 'swim_v1'
): ReportData {
  if (format === 'swim_v1') {
    return {
      ...swimReportV1DemoReport,
      session_id: sessionId,
    }
  }

  const task = tasks.find((item) => item.session_id === sessionId) || demoTask
  return {
    ...demoReport,
    session_id: sessionId,
    task_id: task.id,
  }
}
