import { describe, expect, it } from 'vitest'
import { normalizeReportData } from './reportAdapter'

describe('normalizeReportData diagnostic keyframes', () => {
  it('preserves keyframe semantics and trace fields', () => {
    const viewModel = normalizeReportData({
      schema_version: 'swim-report.v1',
      title: '测试报告',
      sections: [{
        key: 'upper_limb',
        page_type: 'upper_limb_kinematics',
        title: '上肢运动学',
        assets: [{
          key: 'upper_limb.keyframe.left_elbow_min',
          type: 'annotated_frame',
          artifact_type: 'annotated_keyframe',
          module_key: 'upper_limb',
          title: '左肘角最小',
          metric_label: '左肘角',
          value: 82.5,
          unit: '°',
          annotation_frame: 12,
          source_video_frame: 44,
          source_annotation_revision: 3,
          url: '/uploads/keyframe.png',
        }],
      }],
    })

    const asset = viewModel.sections[0].assets?.[0]
    expect(asset?.artifact_type).toBe('annotated_keyframe')
    expect(asset?.metric_label).toBe('左肘角')
    expect(asset?.annotation_frame).toBe(12)
    expect(asset?.source_video_frame).toBe(44)
    expect(asset?.source_annotation_revision).toBe(3)
  })

  it('keeps the full five-page print set and maps persisted AI interpretation', () => {
    const sections = [1, 2, 3, 4, 5].map((page) => ({
      key: `page-${page}`,
      page_number: page,
      page_type: page === 1 ? 'analysis_overview' : `type-${page}`,
      module_key: page === 1 ? 'overview' : `module-${page}`,
      title: `Page ${page}`,
    }))
    const ai = {
      status: 'ready',
      can_regenerate: true,
      content: {
        schema_version: 'swim-report-interpretation.v1',
        plain_language_summary: { text: '通俗总结', fact_refs: ['metric:a'], knowledge_refs: [] },
        module_explanations: [],
        priority_focus: [],
        training_suggestions: [],
        retest_targets: [],
        limitations: [],
      },
    }
    const viewModel = normalizeReportData({
      report: { schema_version: 'swim-report.v1', sections },
      ai_interpretation: ai,
    })
    expect(viewModel.sections).toHaveLength(4)
    expect(viewModel.printSections).toHaveLength(5)
    expect(viewModel.aiInterpretation?.content?.plain_language_summary.text).toBe('通俗总结')
  })
})
