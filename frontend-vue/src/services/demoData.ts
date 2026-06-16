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

let athletes = [...demoAthletes]
let sessions = [...demoSessions]
let sessionVideos = [...demoSessionVideos]
let videoSequence = 9100
let athleteSequence = 200
let sessionSequence = 300
let sessionVideoSequence = 400

export function resetDemoBusinessData() {
  athletes = [...demoAthletes]
  sessions = [...demoSessions]
  sessionVideos = [...demoSessionVideos]
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
