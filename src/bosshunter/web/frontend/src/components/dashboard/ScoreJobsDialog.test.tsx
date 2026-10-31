import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, render, screen } from '@testing-library/react'
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
})
