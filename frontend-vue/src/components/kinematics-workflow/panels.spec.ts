import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import AnalysisProgressPanel from './AnalysisProgressPanel.vue'
import ReportReadyPanel from './ReportReadyPanel.vue'
import { makeTask } from '../../test/factories'
import type { PipelineProgress } from '../../types'

const PROGRESS: PipelineProgress = makeTask().pipeline_progress!

describe('AnalysisProgressPanel (16.13 失败 UI)', () => {
  it('真实失败任务展示失败阶段与错误码', () => {
    const task = makeTask({ status: 'failed', failed_stage: 'generating_artifacts', error_code: 'ARTIFACT_GENERATION_FAILED', actions: ['retry', 'details'] })
    const wrapper = mount(AnalysisProgressPanel, {
      props: {
        progress: task.pipeline_progress!,
        status: task.status,
        failedStage: task.failed_stage,
        errorCode: task.error_code,
        errorMessage: task.error_message,
        actions: task.actions,
        busy: null
      }
    })
    expect(wrapper.text()).toContain('失败阶段')
    expect(wrapper.text()).toContain('ARTIFACT_GENERATION_FAILED')
    expect(wrapper.find('button').exists()).toBe(true)
  })

  it('forceFailed 使 completed 但报告缺失的任务展示失败恢复 UI', () => {
    const task = makeTask({ status: 'completed', error_code: 'REPORT_METADATA_MISSING', failed_stage: 'assembling_report', actions: ['resubmit', 'details'] })
    const wrapper = mount(AnalysisProgressPanel, {
      props: {
        progress: task.pipeline_progress!,
        status: task.status,
        failedStage: task.failed_stage,
        errorCode: task.error_code,
        errorMessage: task.error_message,
        actions: task.actions,
        busy: null,
        forceFailed: true
      }
    })
    expect(wrapper.text()).toContain('REPORT_METADATA_MISSING')
    expect(wrapper.text()).toContain('使用当前标注重新生成')
  })

  it('运行中任务不展示失败框', () => {
    const task = makeTask({ status: 'processing' })
    const wrapper = mount(AnalysisProgressPanel, {
      props: {
        progress: task.pipeline_progress!,
        status: task.status,
        failedStage: null,
        errorCode: null,
        errorMessage: null,
        actions: task.actions,
        busy: null
      }
    })
    expect(wrapper.text()).not.toContain('失败阶段')
  })
})

describe('ReportReadyPanel (13.1/13.5 报告状态)', () => {
  it('freshness=current 展示查看/导出按钮', () => {
    const wrapper = mount(ReportReadyPanel, {
      props: { freshness: 'current', pdfStatus: 'not_exported', pdfUrl: null, pdfBusy: null }
    })
    expect(wrapper.text()).toContain('查看 HTML 报告')
    expect(wrapper.text()).toContain('导出 PDF')
  })

  it('freshness=stale 展示旧版标注警告', () => {
    const wrapper = mount(ReportReadyPanel, {
      props: { freshness: 'stale', reportRevision: 1, selectedRevision: 2, pdfStatus: 'not_exported', pdfUrl: null, pdfBusy: null }
    })
    expect(wrapper.text()).toContain('旧版标注')
  })

  it('freshness=none 展示报告不可用与重新生成动作', () => {
    const wrapper = mount(ReportReadyPanel, {
      props: { freshness: 'none', pdfStatus: 'not_exported', pdfUrl: null, pdfBusy: null }
    })
    expect(wrapper.text()).toContain('报告不可用')
    expect(wrapper.text()).toContain('使用当前标注重新生成')
    // 不渲染查看/导出按钮
    expect(wrapper.text()).not.toContain('查看 HTML 报告')
  })
})
