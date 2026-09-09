import { beforeEach, describe, expect, it } from 'vitest'
import {
  deleteDemoSession,
  getDemoSession,
  getDemoSessionVideos,
  getDemoTasks,
  replaceDemoSessionVideo,
  resetDemoBusinessData
} from './demoData'

describe('demo session deletion', () => {
  beforeEach(() => resetDemoBusinessData())

  it('removes the session, task, and bound videos together', () => {
    const sessionId = 201
    expect(getDemoSession(sessionId)).not.toBeNull()
    expect(getDemoTasks().some((task) => task.session_id === sessionId)).toBe(true)
    expect(getDemoSessionVideos(sessionId)).not.toHaveLength(0)

    deleteDemoSession(sessionId)

    expect(getDemoSession(sessionId)).toBeNull()
    expect(getDemoTasks().some((task) => task.session_id === sessionId)).toBe(false)
    expect(getDemoSessionVideos(sessionId)).toHaveLength(0)
  })

  it('replaces the bound video without changing the session binding id', () => {
    const sessionId = 201
    const before = getDemoSessionVideos(sessionId)
    const current = before[0]
    const replacement = { ...current.video, id: current.video.id + 1000, original_filename: 'replacement.mp4' }

    const updated = replaceDemoSessionVideo(sessionId, current.id, replacement, {
      view_type: 'side',
      fps: 50,
      resolution: '1920x1080',
      sync_offset_ms: 8
    })

    expect(updated.id).toBe(current.id)
    expect(updated.video_file_id).toBe(replacement.id)
    expect(updated.video.original_filename).toBe('replacement.mp4')
    expect(getDemoSessionVideos(sessionId)).toHaveLength(before.length)
    expect(getDemoSessionVideos(sessionId).find((item) => item.id === current.id)?.video_file_id).toBe(replacement.id)
  })
})
