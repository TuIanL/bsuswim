import { describe, expect, it } from 'vitest'
import { groupQualityIssues } from './qualityIssueGrouping'

describe('quality issue grouping', () => {
  it('keeps one issue per code and retains the most severe issue', () => {
    const result = groupQualityIssues([
      { code: 'SCALE_MISSING', severity: 'warning' },
      { code: 'SCALE_MISSING', severity: 'error' },
      { code: 'WATERLINE_MISSING', severity: 'warning' }
    ])
    expect(result).toHaveLength(2)
    expect(result.find((issue) => issue.code === 'SCALE_MISSING')?.severity).toBe('error')
  })
})
