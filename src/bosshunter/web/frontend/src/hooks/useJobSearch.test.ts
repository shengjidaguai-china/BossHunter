import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, renderHook } from '@testing-library/react'
import { useJobSearch } from './useJobSearch'
import { EMPTY_JOB_FILTERS } from '@/lib/jobFilters'

const response = (score: number, total = 2) => new Response(JSON.stringify({
  items: [{ id: 'job-1', score, status: score ? 'scored' : 'pending' }],
  total, all_total: 3, city_options: ['上海'],
}))

beforeEach(() => vi.useFakeTimers())
afterEach(() => {
  cleanup()
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('automatic job refresh', () => {
  it('updates scores, statuses and counts in place while preserving the query and page', async () => {
    const filters = { ...EMPTY_JOB_FILTERS, status: ['pending'] }
    let finishRefresh!: (value: Response) => void
    const fetchMock = vi.fn().mockResolvedValueOnce(response(0))
      .mockImplementationOnce(() => new Promise<Response>(resolve => { finishRefresh = resolve }))
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useJobSearch(filters, 2, 15, 'score', 'desc'))
    await act(async () => {})
    expect(result.current.items[0].score).toBe(0)
    await act(async () => { await vi.advanceTimersByTimeAsync(5000) })
    expect(result.current.loading).toBe(false)
    expect(result.current.items[0].status).toBe('pending')
    // Slow requests must not accumulate another fetch on each timer tick.
    await act(async () => { await vi.advanceTimersByTimeAsync(5000) })
    expect(fetchMock).toHaveBeenCalledTimes(2)
    await act(async () => { finishRefresh(response(88, 1)) })
    expect(result.current.items[0].score).toBe(88)
    expect(result.current.items[0].status).toBe('scored')
    expect(result.current.total).toBe(1)
    expect(result.current.allTotal).toBe(3)
    expect(result.current.lastRefreshedAt).not.toBeNull()
    const url = new URL(fetchMock.mock.calls[1][0], 'http://localhost')
    expect(url.searchParams.get('offset')).toBe('30')
    expect(url.searchParams.getAll('status')).toEqual(['pending'])
    expect(url.searchParams.get('sort_by')).toBe('score')
  })

  it('polls when embedded visibility reports hidden and refreshes immediately on focus', async () => {
    vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden')
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(response(80)))
    vi.stubGlobal('fetch', fetchMock)
    const { unmount } = renderHook(() => useJobSearch(EMPTY_JOB_FILTERS, 0, 15))
    await act(async () => {})
    await act(async () => { await vi.advanceTimersByTimeAsync(5000) })
    expect(fetchMock).toHaveBeenCalledTimes(2)
    await act(async () => { window.dispatchEvent(new Event('focus')) })
    expect(fetchMock).toHaveBeenCalledTimes(3)
    unmount()
    await act(async () => { await vi.advanceTimersByTimeAsync(10000) })
    window.dispatchEvent(new Event('focus'))
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('times out a stuck request and recovers on the next poll', async () => {
    const fetchMock = vi.fn().mockImplementationOnce((_url, options) => new Promise((_resolve, reject) => {
      options.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
    })).mockImplementation(() => Promise.resolve(response(90)))
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useJobSearch(EMPTY_JOB_FILTERS, 0, 15))
    await act(async () => { await vi.advanceTimersByTimeAsync(15000) })
    await act(async () => { await vi.advanceTimersByTimeAsync(5000) })
    expect(fetchMock.mock.calls[0][1].signal.aborted).toBe(true)
    expect(result.current.items[0].score).toBe(90)
    expect(result.current.error).toBe('')
    expect(result.current.loading).toBe(false)
  })

  it('ignores an old response when the user changes page during a refresh', async () => {
    let finishOld!: (value: Response) => void
    const fetchMock = vi.fn().mockImplementationOnce(() => new Promise<Response>(resolve => { finishOld = resolve }))
      .mockResolvedValueOnce(response(92))
    vi.stubGlobal('fetch', fetchMock)
    const { result, rerender } = renderHook(({ page }) => useJobSearch(EMPTY_JOB_FILTERS, page, 15), { initialProps: { page: 0 } })
    rerender({ page: 1 })
    await act(async () => {})
    expect(result.current.items[0].score).toBe(92)
    expect(fetchMock.mock.calls[0][1].signal.aborted).toBe(true)
    await act(async () => { finishOld(response(10)) })
    expect(result.current.items[0].score).toBe(92)
  })
})
