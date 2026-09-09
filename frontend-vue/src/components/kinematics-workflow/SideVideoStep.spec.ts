import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import SideVideoStep from './SideVideoStep.vue'

const boundVideo = {
  id: 7,
  session_id: 1,
  video_file_id: 11,
  view_type: 'side' as const,
  fps: 60,
  resolution: '1920x1080',
  sync_offset_ms: 0,
  created_at: new Date().toISOString(),
  video: {
    id: 11,
    original_filename: 'old.mp4',
    stored_filename: 'old.mp4',
    storage_path: 'old.mp4',
    mime_type: 'video/mp4',
    size_bytes: 10,
    checksum_sha256: 'old',
    created_at: new Date().toISOString(),
    playback_url: ''
  }
}

describe('SideVideoStep replacement flow', () => {
  it('emits the selected file from the replacement picker', async () => {
    const wrapper = mount(SideVideoStep, {
      props: { video: boundVideo },
      global: {
        stubs: {
          VideoCamera: true
        }
      }
    })
    const file = new File(['video'], 'replacement.mp4', { type: 'video/mp4' })
    const input = wrapper.get('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [file] })

    await input.trigger('change')

    expect(wrapper.emitted('replace')).toEqual([[file]])
  })
})
