import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AIInterpretationPanel from './AIInterpretationPanel.vue'
import type { AIInterpretationEnvelope } from '../../types'

function readyInterpretation(): AIInterpretationEnvelope {
  return {
    status: 'ready',
    can_regenerate: true,
    trace: {
      generation_signature: 'ai-sig',
      base_report_generation_signature: 'report-sig',
      provider: 'fake',
      model: 'test-model',
      prompt_version: 'v1',
      output_schema_version: 'v1',
      knowledge_base_version: 'kb-v1',
      knowledge_ids: ['body@1'],
    },
    content: {
      schema_version: 'swim-report-interpretation.v1',
      plain_language_summary: {
        text: '这是一段很长但有边界的通俗总结。',
        fact_refs: ['metric:body_angle_std_deg'],
        knowledge_refs: [],
      },
      module_explanations: [
        {
          module_key: 'body_posture_head_trunk',
          text: '身体模块说明',
          fact_refs: ['metric:body_angle_std_deg'],
          knowledge_refs: [],
        },
        {
          module_key: 'upper_limb',
          text: '上肢模块说明',
          fact_refs: ['metric:elbow_rom_deg'],
          knowledge_refs: [],
        },
      ],
      priority_focus: [{ text: '优先复核身体姿态', fact_refs: ['finding:body'], knowledge_refs: [] }],
      training_suggestions: [{
        title: '身体姿态练习',
        text: '可尝试低强度练习。',
        applicability: '经教练确认后采用。',
        cautions: [],
        fact_refs: ['finding:body'],
        knowledge_refs: ['body'],
      }],
      retest_targets: [],
      limitations: ['AI 解读不替代教练判断。'],
    },
  }
}

describe('AIInterpretationPanel', () => {
  it('renders overview with fact references', () => {
    const wrapper = mount(AIInterpretationPanel, {
      props: { interpretation: readyInterpretation(), moduleKey: 'analysis_overview' },
    })
    expect(wrapper.text()).toContain('通俗总结')
    expect(wrapper.text()).toContain('metric:body_angle_std_deg')
    expect(wrapper.text()).toContain('test-model')
  })

  it('does not copy explanations across modules', () => {
    const wrapper = mount(AIInterpretationPanel, {
      props: { interpretation: readyInterpretation(), moduleKey: 'upper_limb' },
    })
    expect(wrapper.text()).toContain('上肢模块说明')
    expect(wrapper.text()).not.toContain('身体模块说明')
  })

  it('renders review suggestions, limitations, and knowledge references', () => {
    const wrapper = mount(AIInterpretationPanel, {
      props: { interpretation: readyInterpretation(), moduleKey: 'review_summary' },
    })
    expect(wrapper.text()).toContain('身体姿态练习')
    expect(wrapper.text()).toContain('AI 解读不替代教练判断')
    expect(wrapper.text()).toContain('body')
  })

  it('renders v3 layers and only links resolvable catalog references', () => {
    const interpretation = readyInterpretation()
    interpretation.content!.schema_version = 'swim-report-interpretation.v3'
    interpretation.content!.plain_language_summary = {
      text: 'v3 总结',
      observation: '观察到身体轴角波动。',
      possible_explanations: ['可能受到机位影响'],
      potential_impact: '作为复核线索。',
      action: '查看对应指标。',
      fact_refs: ['metric:body_angle_std_deg'],
      knowledge_refs: ['body'],
    }
    interpretation.references = [
      {
        reference_id: 'metric:body_angle_std_deg',
        reference_type: 'fact',
        label: '身体轴角波动',
        anchor: 'report-ref-metric-body_angle_std_deg',
        target_available: true,
      },
      {
        reference_id: 'body',
        reference_type: 'knowledge',
        label: '知识依据',
        target_available: false,
      },
    ]
    const wrapper = mount(AIInterpretationPanel, {
      props: { interpretation, moduleKey: 'analysis_overview' },
    })
    expect(wrapper.text()).toContain('观察到身体轴角波动')
    expect(wrapper.find('a[href="#report-ref-metric-body_angle_std_deg"]').exists()).toBe(true)
    expect(wrapper.find('.ai-ref-link--unavailable').text()).toContain('知识依据')
    expect(wrapper.find('.ai-ref-link--unavailable').element.tagName).toBe('SPAN')
  })

  it.each(['pending', 'generating', 'failed', 'stale', 'not_configured'] as const)(
    'shows compact %s state without partial content',
    (status) => {
      const wrapper = mount(AIInterpretationPanel, {
        props: {
          interpretation: {
            status,
            can_regenerate: status === 'failed',
            error: status === 'failed' ? { code: 'failed', message: '生成失败', retryable: true } : null,
          },
          moduleKey: 'analysis_overview',
        },
      })
      expect(wrapper.attributes('data-ai-interpretation-status')).toBe(status)
      expect(wrapper.text()).not.toContain('通俗总结')
    },
  )
})
