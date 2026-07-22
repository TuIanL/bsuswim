import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import PrintReportView from '../views/PrintReportView.vue'
import { useRoute } from 'vue-router'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { sessionId: '1' }, query: { token: 't' } }),
  useRouter: () => ({ push: vi.fn() }),
}))

async function settle() {
  for (let i = 0; i < 5; i++) {
    await nextTick()
    await Promise.resolve()
  }
}

function makeReport(sections: number[]) {
  return {
    report_data: {
      schema_version: 'swim-report.v1',
      report_profile: 'side_2d_kinematics_5page_v1',
      generation_signature: 'sig-abc-123',
      sections: sections.map((n) => ({
        key: `page-${n}`,
        page_number: n,
        page_type: `type-${n}`,
        module_key: `module-${n}`,
        title: `Page ${n}`,
        metrics: [],
        findings: [],
        assets: [],
      })),
    },
  }
}

describe('PrintReportView', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    // jsdom lacks document.fonts
    ;(document as any).fonts = { ready: Promise.resolve() }
    ;(window as any).__REPORT_PRINT_READY__ = false
    ;(window as any).__REPORT_PRINT_ERROR__ = undefined
  })

  it('renders exactly one print-page per report section (no cover page)', async () => {
    const data = makeReport([1, 2, 3, 4, 5])
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => data,
    }))

    const wrapper = mount(PrintReportView, {
      props: { sessionId: '1', token: 't' } as any,
    })

    await settle()

    const pages = wrapper.findAll('.print-page')
    expect(pages).toHaveLength(5)
  })

  it('sets page semantic attributes from the report sections', async () => {
    const data = makeReport([1, 2, 3, 4, 5])
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => data }))

    const wrapper = mount(PrintReportView, {
      props: { sessionId: '1', token: 't' } as any,
    })

    await settle()

    const root = wrapper.find('.print-report')
    expect(root.attributes('data-report-generation-signature')).toBe('sig-abc-123')

    const pages = wrapper.findAll('.print-page')
    expect(pages[2].attributes('data-page-number')).toBe('3')
    expect(pages[2].attributes('data-page-type')).toBe('type-3')
    expect(pages[2].attributes('data-module-key')).toBe('module-3')
  })

  it('does not set __REPORT_PRINT_READY__ unconditionally in finally', async () => {
    // Fail the fetch; ready must NOT be set, and error must be recorded.
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({}) }))

    mount(PrintReportView, {
      props: { sessionId: '1', token: 't' } as any,
    })

    await settle()

    expect((window as any).__REPORT_PRINT_READY__).toBeFalsy()
    expect((window as any).__REPORT_PRINT_ERROR__).toBeTruthy()
    expect((window as any).__REPORT_PRINT_ERROR__.code).toBe('PRINT_DATA_LOAD_FAILED')
  })
})
