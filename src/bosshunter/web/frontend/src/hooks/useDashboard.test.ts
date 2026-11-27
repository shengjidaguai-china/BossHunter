import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { useDashboard, type Job } from './useDashboard'

const jsonResponse = (body: unknown) => new Response(JSON.stringify(body))

afterEach(() => {
  cleanup()
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('greeting save and dashboard refresh', () => {
  it('keeps the saved final version when an older refresh finishes later', async () => {
    const original = { id: 'greeting-1', greeting: '原文', greeting_selection: 'original' } as Job
    const saved = { ...original, greeting: '刚刚确认的编辑版本', greeting_selection: 'edited' }
    const workbench = {
      pending_confirmation: [], pending_greetings: [original], send_errors: [], needs_resume: [],
    }
    const fetchMock = vi.fn(() => Promise.resolve(jsonResponse(workbench)))
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useDashboard('workbench'))
    await waitFor(() => expect(result.current.loading).toBe(false))

    let finishOldRefresh!: (value: Response) => void
    fetchMock.mockImplementationOnce(() => new Promise<Response>(resolve => { finishOldRefresh = resolve }))
    let oldRefresh!: Promise<void>
    act(() => { oldRefresh = result.current.refresh() })
    act(() => { result.current.updateGreetingJob(saved) })
    expect(result.current.workbench.pending_greetings[0].greeting).toBe(saved.greeting)
    await act(async () => {
      finishOldRefresh(jsonResponse(workbench))
      await oldRefresh
    })
    expect(result.current.workbench.pending_greetings[0].greeting).toBe(saved.greeting)
    expect(result.current.workbench.pending_greetings[0].greeting_selection).toBe('edited')

    const later = { ...saved, greeting: '稍后在另一个页面确认的版本' }
    fetchMock.mockResolvedValueOnce(jsonResponse({ ...workbench, pending_greetings: [later] }))
    await act(async () => { await result.current.refresh() })
    expect(result.current.workbench.pending_greetings[0].greeting).toBe(later.greeting)
  })
})


describe('dashboard progress polling', () => {
  it('updates progress even when the embedded document reports hidden', async () => {
    vi.useFakeTimers()
    vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden')
    let completed = 1
    const fetchMock = vi.fn(async () => jsonResponse({ task: { metrics: { ai_completed: completed } } }))
    vi.stubGlobal('fetch', fetchMock)
    const { result, unmount } = renderHook(() => useDashboard('workbench'))
    await act(async () => {})
    expect(result.current.workbench.task?.metrics?.ai_completed).toBe(1)
    completed = 2
    await act(async () => { await vi.advanceTimersByTimeAsync(5000) })
    expect(result.current.workbench.task?.metrics?.ai_completed).toBe(2)
    expect(fetchMock).toHaveBeenCalledTimes(2)
    unmount()
    await act(async () => { await vi.advanceTimersByTimeAsync(10000) })
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('releases a timed out poll so later progress can be read', async () => {
    vi.useFakeTimers()
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const fetchMock = vi.fn().mockImplementationOnce((_url, options) => new Promise((_resolve, reject) => {
      options.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
    })).mockImplementation(() => Promise.resolve(jsonResponse({ task: { metrics: { ai_completed: 3 } } })))
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useDashboard('workbench'))
    await act(async () => { await vi.advanceTimersByTimeAsync(15000) })
    await act(async () => { await vi.advanceTimersByTimeAsync(5000) })
    expect(fetchMock.mock.calls[0][1].signal.aborted).toBe(true)
    expect(result.current.workbench.task?.metrics?.ai_completed).toBe(3)
    expect(result.current.error).toBe('')
    expect(result.current.refreshing).toBe(false)
  })

  it('aborts and ignores a poll left over from a previous scope', async () => {
    vi.useFakeTimers()
    let finishOld!: (value: Response) => void
    const fetchMock = vi.fn().mockImplementationOnce(() => new Promise<Response>(resolve => { finishOld = resolve }))
      .mockResolvedValueOnce(jsonResponse([]))
    vi.stubGlobal('fetch', fetchMock)
    const { result, rerender } = renderHook(({ scope }: { scope: 'workbench' | 'monitor' }) => useDashboard(scope), { initialProps: { scope: 'workbench' as 'workbench' | 'monitor' } })
    rerender({ scope: 'monitor' })
    await act(async () => {})
    expect(fetchMock.mock.calls[0][1].signal.aborted).toBe(true)
    await act(async () => { finishOld(jsonResponse({ task: { metrics: { ai_completed: 99 } } })) })
    expect(result.current.workbench.task).toBeNull()
    expect(result.current.history).toEqual([])
  })
})
