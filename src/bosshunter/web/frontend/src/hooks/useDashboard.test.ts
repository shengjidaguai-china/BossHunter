import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { useDashboard, type Job } from './useDashboard'

const jsonResponse = (body: unknown) => new Response(JSON.stringify(body))

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
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
