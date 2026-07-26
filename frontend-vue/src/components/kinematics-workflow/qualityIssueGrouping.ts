import type { QualityIssue } from '../../types'

export function groupQualityIssues(issues: QualityIssue[]): QualityIssue[] {
  const grouped = new Map<string, QualityIssue>()
  const rank = (value?: string) => value === 'error' ? 3 : value === 'warning' ? 2 : 1
  for (const issue of issues) {
    const existing = grouped.get(issue.code)
    if (!existing || rank(issue.severity) > rank(existing.severity)) grouped.set(issue.code, issue)
  }
  return [...grouped.values()]
}
