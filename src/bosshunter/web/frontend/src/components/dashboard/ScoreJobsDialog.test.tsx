import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { ScoreJobsDialog } from './ScoreJobsDialog'

afterEach(() => {
  cleanup()
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('ScoreJobsDialog progress polling', () => {
  it('refreshes an active run and stops polling when the dialog closes', async () => {
    vi.useFakeTimers()
    let completed = 1
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => new Response(JSON.stringify(
      String(input) === '/api/scoring/runs'
        ? [{ id: 'run-1', status: 'running', remaining_job_ids: ['a', 'b'], progress: { ai_total: 4, ai_completed: completed } }]
        : { eligible_jobs: 0 }
    ), { status: 200, headers: { 'Content-Type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)
    const props = { selectedJobIds: [], onClose: vi.fn(), onStart: vi.fn() }
    const { rerender } = render(<ScoreJobsDialog open {...props} />)
    await act(async () => { await vi.advanceTimersByTimeAsync(0) })
    expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('25')
    completed = 2
    await act(async () => { await vi.advanceTimersByTimeAsync(3000) })
    expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('50')
    rerender(<ScoreJobsDialog open={false} {...props} />)
    const calls = fetchMock.mock.calls.length
    await act(async () => { await vi.advanceTimersByTimeAsync(6000) })
    expect(fetchMock.mock.calls.length).toBe(calls)
  })

  it('does not start an overlapping poll while the previous run response is slow', async () => {
    vi.useFakeTimers()
    let resolveFirst!: (value: Response) => void
    let resolveSecond!: (value: Response) => void
    let runCalls = 0
    const runResponse = (completed: number) => new Response(JSON.stringify([
      { id: 'run-1', status: 'running', remaining_job_ids: ['a', 'b'], progress: { ai_total: 4, ai_completed: completed } },
    ]), { status: 200, headers: { 'Content-Type': 'application/json' } })
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      if (String(input) === '/api/scoring/runs') {
        runCalls += 1
        return new Promise<Response>(resolve => {
          if (runCalls === 1) resolveFirst = resolve
          else resolveSecond = resolve
        })
      }
      return Promise.resolve(new Response(JSON.stringify({ eligible_jobs: 0 }), { status: 200 }))
    })
    vi.stubGlobal('fetch', fetchMock)
    const props = { selectedJobIds: [], onClose: vi.fn(), onStart: vi.fn() }
    render(<ScoreJobsDialog open {...props} />)

    await act(async () => { await vi.advanceTimersByTimeAsync(3000) })
    expect(runCalls).toBe(1)
    await act(async () => { resolveFirst(runResponse(1)) })
    expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('25')

    await act(async () => { await vi.advanceTimersByTimeAsync(3000) })
    expect(runCalls).toBe(2)
    await act(async () => { resolveSecond(runResponse(2)) })
    expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('50')
  })

})


describe('ScoreJobsDialog cooperative end', () => {
  it('keeps an ending run visible and blocks another start until it exits', async () => {
    let status = 'running'
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/end')) status = 'stopping'
      const run = { id: 'run-1', status, remaining_job_ids: ['a'], progress: {} }
      return new Response(JSON.stringify(
        url === '/api/scoring/runs' ? [run] : url.endsWith('/end') ? run : { eligible_jobs: 1 }
      ), { status: url.endsWith('/end') ? 202 : 200 })
    }))
    render(<ScoreJobsDialog open selectedJobIds={[]} onClose={vi.fn()} onStart={vi.fn()} />)
    fireEvent.click(await screen.findByRole('button', { name: '结束' }))
    expect(await screen.findByText('正在结束 · 剩余 1 个岗位')).toBeTruthy()
    expect(await screen.findByText('已请求结束，正在等待评分处理退出。')).toBeTruthy()
    expect((screen.getByRole('button', { name: '结束' }) as HTMLButtonElement).disabled).toBe(true)
    expect((screen.getByRole('button', { name: '确认开始评分' }) as HTMLButtonElement).disabled).toBe(true)
  })
})
