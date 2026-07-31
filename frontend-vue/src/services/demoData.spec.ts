import { beforeEach, describe, expect, it } from 'vitest'
import { deleteDemoSession, getDemoSession, getDemoSessionVideos, getDemoTasks, resetDemoBusinessData } from './demoData'

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
})
