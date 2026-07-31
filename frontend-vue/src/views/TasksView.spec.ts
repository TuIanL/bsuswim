import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import TasksView from './TasksView.vue'

const { confirm, remove, listSessions, listTasks } = vi.hoisted(() => ({
  confirm: vi.fn(), remove: vi.fn(), listSessions: vi.fn(), listTasks: vi.fn()
}))

vi.mock('../services/api', () => ({ deleteSession: remove, listSessions, listTasks }))
vi.mock('element-plus', () => ({ ElMessage: { success: vi.fn(), error: vi.fn() }, ElMessageBox: { confirm } }))

async function settle() {
  await nextTick()
  await Promise.resolve()
  await nextTick()
}

describe('TasksView deletion', () => {
  beforeEach(() => {
    confirm.mockResolvedValue(undefined)
    remove.mockResolvedValue(undefined)
    listSessions.mockResolvedValue([{ id: 1, title: '待删除测试', stroke_type: 'freestyle', status: 'completed', created_at: '', updated_at: '' }])
    listTasks.mockResolvedValue([])
  })

  it('confirms permanent deletion and refreshes the list', async () => {
    const wrapper = mount(TasksView)
    await settle()
    const deleteButton = wrapper.findAll('button').find((button) => button.text() === '删除')
    expect(deleteButton).toBeTruthy()
    await deleteButton!.trigger('click')
    await settle()
    expect(confirm).toHaveBeenCalled()
    expect(remove).toHaveBeenCalledWith(1)
    expect(listSessions).toHaveBeenCalledTimes(2)
  })
})
