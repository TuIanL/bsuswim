import { nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AnnotationQualityRepairWorkbench from './AnnotationQualityRepairWorkbench.vue'

const api = vi.hoisted(() => ({
  getNormalizedAnnotation: vi.fn(),
  repairAnnotationQuality: vi.fn(),
  resolveMediaUrl: vi.fn()
}))

vi.mock('../../services/api', () => api)

const video = {
  fps: 60,
  video: { playback_url: '/uploads/test.mp4' }
} as any

function mountWorkbench() {
  return mount(AnnotationQualityRepairWorkbench, {
    props: {
      visible: true,
      normalizedAnnotationId: 1,
      video
    },
    attachTo: document.body,
    global: {
      stubs: {
        'el-dialog': { template: '<div><slot /></div>' },
        'el-button': { props: ['disabled', 'loading'], template: '<button :disabled="disabled"><slot /></button>' },
        'el-steps': { template: '<div><slot /></div>' },
        'el-step': { template: '<span><slot /></span>' },
        'el-slider': { template: '<input type="range" />' },
        'el-input-number': { template: '<input type="number" />' },
        'el-radio-group': { template: '<div><slot /></div>' },
        'el-radio-button': { template: '<button><slot /></button>' },
        'el-checkbox': { template: '<label><input type="checkbox" /><slot /></label>' },
        'el-alert': { template: '<div><slot /><span>{{ title }}</span></div>', props: ['title'] }
      }
    }
  })
}

function button(wrapper: ReturnType<typeof mountWorkbench>, label: string) {
  const match = wrapper.findAll('button').find((item) => item.text().includes(label))
  expect(match, `button ${label} should exist`).toBeTruthy()
  return match!
}

async function loadVideo(wrapper: ReturnType<typeof mountWorkbench>) {
  const element = wrapper.get('video').element as HTMLVideoElement
  Object.defineProperties(element, {
    videoWidth: { value: 640, configurable: true },
    videoHeight: { value: 360, configurable: true },
    duration: { value: 2, configurable: true },
    currentTime: { value: 0, writable: true, configurable: true }
  })
  const canvas = wrapper.get('canvas').element as HTMLCanvasElement
  vi.spyOn(canvas, 'getBoundingClientRect').mockReturnValue({
    x: 0,
    y: 0,
    width: 640,
    height: 360,
    top: 0,
    right: 640,
    bottom: 360,
    left: 0,
    toJSON: () => ({})
  })
  vi.spyOn(canvas, 'getContext').mockReturnValue({
    scale: vi.fn(), clearRect: vi.fn(), beginPath: vi.fn(), moveTo: vi.fn(),
    lineTo: vi.fn(), stroke: vi.fn(), arc: vi.fn(), fill: vi.fn()
  } as any)
  element.dispatchEvent(new Event('loadedmetadata'))
  await nextTick()
  return element
}

beforeEach(() => {
  vi.clearAllMocks()
  api.resolveMediaUrl.mockReturnValue('/uploads/test.mp4')
  api.getNormalizedAnnotation.mockResolvedValue({
    id: 1,
    revision: 3,
    swim_direction: null,
    events: [],
    annotation_metadata: {}
  })
  api.repairAnnotationQuality.mockResolvedValue({ revision: 4 })
})

describe('AnnotationQualityRepairWorkbench', () => {
  it('supports scale, waterline, direction, events and mapping steps', async () => {
    const wrapper = mountWorkbench()
    const element = await loadVideo(wrapper)

    await wrapper.get('canvas').trigger('click', { clientX: 100, clientY: 100 })
    await wrapper.get('canvas').trigger('click', { clientX: 500, clientY: 100 })
    expect(wrapper.text()).toContain('16.00 px/m')

    await button(wrapper, '下一步').trigger('click')
    expect(wrapper.text()).toContain('水面线')
    await button(wrapper, '下一步').trigger('click')
    expect(wrapper.text()).toContain('左 → 右')
    await button(wrapper, '下一步').trigger('click')
    expect(wrapper.text()).toContain('标记当前帧为入水')

    Object.defineProperty(element, 'currentTime', { value: 0.5, writable: true, configurable: true })
    element.dispatchEvent(new Event('timeupdate'))
    await nextTick()
    await button(wrapper, '标记当前帧为入水').trigger('click')
    expect(wrapper.text()).toContain('帧 30')

    await button(wrapper, '下一步').trigger('click')
    expect(wrapper.text()).toContain('确认标注帧与视频帧')
    expect(wrapper.text()).toContain('固定偏移')
  })

  it('video load failure disables visual operations and shows an explicit error', async () => {
    const wrapper = mountWorkbench()
    await wrapper.get('video').trigger('error')
    await nextTick()

    expect(wrapper.text()).toContain('视频无法加载，画布标注已禁用')
    expect(button(wrapper, '上一帧').attributes('disabled')).toBeDefined()
    await button(wrapper, '下一步').trigger('click')
    await button(wrapper, '下一步').trigger('click')
    await button(wrapper, '下一步').trigger('click')
    expect(button(wrapper, '标记当前帧为入水').attributes('disabled')).toBeDefined()
  })

  it('refreshes the revision and shows a conflict after a 409 response', async () => {
    const wrapper = mountWorkbench()
    await loadVideo(wrapper)
    await wrapper.get('canvas').trigger('click', { clientX: 100, clientY: 100 })
    await wrapper.get('canvas').trigger('click', { clientX: 500, clientY: 100 })
    api.repairAnnotationQuality.mockRejectedValue({
      response: { status: 409, data: { detail: { message: 'revision conflict' } } }
    })
    api.getNormalizedAnnotation
      .mockResolvedValueOnce({ id: 1, revision: 3, swim_direction: null, events: [], annotation_metadata: {} })
      .mockResolvedValueOnce({ id: 1, revision: 4, swim_direction: null, events: [], annotation_metadata: {} })

    await button(wrapper, '保存并重新验证').trigger('click')
    await nextTick()

    expect(api.repairAnnotationQuality).toHaveBeenCalledWith(1, expect.objectContaining({ expected_revision: 3 }))
    expect(api.getNormalizedAnnotation).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('revision conflict')
  })
})
