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
})
