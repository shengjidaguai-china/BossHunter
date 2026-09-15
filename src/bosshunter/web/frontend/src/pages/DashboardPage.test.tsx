import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import DashboardPage from './DashboardPage'
import type { WorkbenchTask } from '@/hooks/useDashboard'

let workbenchPayload: Record<string, unknown> = {}
let stopResponse: () => Response = () => jsonResponse({})

function jsonResponse(body: unknown, ok = true) {
  return new Response(JSON.stringify(body), {
    status: ok ? 200 : 500,
    headers: { 'Content-Type': 'application/json' },
  })
}

function buildTask(overrides: Partial<WorkbenchTask>): WorkbenchTask {
  return {
    id: 'task-1',
    mode: 'greet',
    label: '生成招呼语',
    status: 'running',
    logs: [],
    stop_requested: false,
    ...overrides,
  }
}

function baseWorkbench(overrides: Record<string, unknown> = {}) {
  return {
    funnel: {},
    funnel_today: {},
    pending_confirmation: [],
    pending_greetings: [],
    send_errors: [],
    needs_resume: [],
    send_quota: { daily_limit: 30, sent: 0, remaining: 30, exhausted: false },
    task: null,
    last_task: null,
    ...overrides,
  }
}

const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
  const url = String(input)
  if (url === '/api/workbench' && (!init?.method || init.method === 'GET')) {
    return jsonResponse(workbenchPayload)
  }
  if (url.includes('/stop') && init?.method === 'POST') {
    return stopResponse()
  }
  return jsonResponse({})
})

describe('DashboardPage workbench task panel', () => {
  beforeEach(() => {
    workbenchPayload = baseWorkbench()
    stopResponse = () => jsonResponse({})
    vi.stubGlobal('fetch', fetchMock)
    fetchMock.mockClear()
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('shows per-job greet progress from task logs', async () => {
    workbenchPayload = baseWorkbench({
      task: buildTask({
        status: 'running',
        logs: ['开始为 3 个岗位生成招呼语', '生成招呼语 (2/3)：字节跳动｜后端工程师'],
      }),
    })
    render(<DashboardPage view="workbench" />)
    expect(await screen.findByText('生成招呼语 (2/3)：字节跳动｜后端工程师')).toBeTruthy()
  })

  it('shows the latest greeting queue progress directly and preserves line breaks', async () => {
    const latestProgress = '招呼语进度：2/3\n成功 1，失败 1，待处理 1'
    workbenchPayload = baseWorkbench({
      task: buildTask({
        mode: 'full',
        label: '全流程',
        logs: ['招呼语进度：1/3', latestProgress, '正在等待下一次发送窗口'],
      }),
    })
    render(<DashboardPage view="workbench" />)
    const progress = await screen.findByText(latestProgress, { normalizer: text => text })
    expect(screen.getByText('任务运行状态')).toBeTruthy()
    expect(progress.textContent).toBe(latestProgress)
    expect(progress.classList.contains('whitespace-pre-line')).toBe(true)
    expect(progress.closest('details:not([open]), [hidden], [aria-hidden="true"]')).toBeNull()
    expect(screen.queryByText('招呼语进度：1/3')).toBeNull()
    expect(screen.getByRole('button', { name: '停止任务' })).toBeTruthy()
  })

  it('shows the pause reason when a greet task completed with partial success', async () => {
    workbenchPayload = baseWorkbench({
      last_task: buildTask({
        status: 'completed',
        metrics: {
          greet_generated: 3,
          greet_preserved: 1,
          greet_failed: 0,
          greet_paused: 1,
          greet_pause_reason: 'AI Token 额度或账户余额不足 (token_quota, status=402)',
        },
      }),
    })
    render(<DashboardPage view="workbench" />)
    expect(await screen.findByText('提前暂停原因：AI 额度或账户余额不足。已生成内容已保存，剩余岗位下次运行会继续处理。')).toBeTruthy()
    expect(screen.getByText('提前暂停')).toBeTruthy()
  })

  it('shows failure feedback and the raw error for a zero-output greet task', async () => {
    workbenchPayload = baseWorkbench({
      last_task: buildTask({
        status: 'failed',
        error: '招呼语生成已安全暂停：AI 服务触发请求或 Token 频率限制 (rate_limit, status=429)',
      }),
    })
    const { container } = render(<DashboardPage view="workbench" />)
    expect(await screen.findByText('任务运行失败')).toBeTruthy()
    expect(container.textContent).toContain('招呼语生成已安全暂停：AI 服务触发请求或 Token 频率限制 (rate_limit, status=429)')
  })

  it('recovers the notice and surfaces the real error when stopping fails', async () => {
    workbenchPayload = baseWorkbench({
      task: buildTask({ mode: 'collect', label: '单独采集', status: 'running' }),
    })
    stopResponse = () => jsonResponse({ error: '任务已结束，无法停止' }, false)
    const confirmSpy = vi.fn(() => true)
    vi.stubGlobal('confirm', confirmSpy)
    render(<DashboardPage view="workbench" />)
    const stopButton = await screen.findByRole('button', { name: '停止任务' })
    fireEvent.click(stopButton)
    expect(confirmSpy).toHaveBeenCalled()
    await waitFor(() => {
      expect(screen.getAllByText('单独采集停止失败：任务已结束，无法停止').length).toBeGreaterThan(0)
    })
  })

  it('confirms the stop request when the backend accepts it', async () => {
    workbenchPayload = baseWorkbench({
      task: buildTask({ mode: 'collect', label: '单独采集', status: 'running' }),
    })
    stopResponse = () => jsonResponse(buildTask({ mode: 'collect', label: '单独采集', status: 'stopping', stop_requested: true }))
    vi.stubGlobal('confirm', () => true)
    render(<DashboardPage view="workbench" />)
    const stopButton = await screen.findByRole('button', { name: '停止任务' })
    fireEvent.click(stopButton)
    await waitFor(() => {
      expect(screen.getAllByText('单独采集已请求停止。').length).toBeGreaterThan(0)
    })
  })
  it('displays the final edited version alongside both generated candidates', async () => {
    workbenchPayload = baseWorkbench({ pending_greetings: [{
      id: 'final-preview', company: '测试公司', title: '测试岗位', status: 'ready',
      greeting: '手动修改后最终发送的文字', greeting_original: 'AI 原始候选',
      greeting_optimized: 'AI 优化候选', greeting_selection: 'edited',
      greeting_reviewed_at: '2026-09-09 12:00:00',
    }] })
    render(<DashboardPage view="workbench" />)
    const finalVersion = await screen.findByLabelText('最终发送版本')
    expect(within(finalVersion).getByText('手动修改后最终发送的文字')).toBeTruthy()
    expect(screen.getByText('AI 原始候选')).toBeTruthy()
    expect(screen.getByText('AI 优化候选')).toBeTruthy()
  })

  it('blocks individual and batch sends until an edit is saved and refreshed', async () => {
    const job = {
      id: 'saving-preview', company: '测试公司', title: '测试岗位', status: 'ready',
      greeting: '原始版本', greeting_original: '原始版本', greeting_optimized: '优化版本',
      greeting_selection: 'original', greeting_reviewed_at: '2026-09-09 12:00:00',
    }
    workbenchPayload = baseWorkbench({ pending_greetings: [job] })
    render(<DashboardPage view="workbench" />)
    fireEvent.click(await screen.findByRole('button', { name: '手动编辑' }))
    const send = screen.getByRole('button', { name: '发送招呼语' }) as HTMLButtonElement
    const batchSend = screen.getByRole('button', { name: '发送已确认 1 个' }) as HTMLButtonElement
    expect(send.disabled).toBe(true)
    expect(batchSend.disabled).toBe(true)
    fireEvent.change(screen.getByLabelText('手动编辑最终版本'), { target: { value: '保存后真正发送的文字' } })
    let finishSave!: (response: Response) => void
    fetchMock.mockImplementationOnce(() => new Promise<Response>(resolve => { finishSave = resolve }))
    fireEvent.click(screen.getByRole('button', { name: '保存编辑版' }))
    expect(send.disabled).toBe(true)
    expect(batchSend.disabled).toBe(true)
    const saved = { ...job, greeting: '保存后真正发送的文字', greeting_selection: 'edited' }
    workbenchPayload = baseWorkbench({ pending_greetings: [saved] })
    finishSave(jsonResponse(saved))
    await waitFor(() => expect(send.disabled).toBe(false))
    expect(batchSend.disabled).toBe(false)
    expect(within(screen.getByLabelText('最终发送版本')).getByText(saved.greeting)).toBeTruthy()
  })

})
