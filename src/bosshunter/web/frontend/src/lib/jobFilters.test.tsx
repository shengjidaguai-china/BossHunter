import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react'
import { EMPTY_JOB_FILTERS, filterJobs } from './jobFilters'
import { JobFilterBar } from '@/components/jobs/JobFilterBar'
import { useJobSearch } from '@/hooks/useJobSearch'
import type { Job } from '@/hooks/useDashboard'

const jobs = [0, 1, 3, 7, 30, null].map((days, index) => ({
  id: String(index), hr_active_days: days, hr_active: '', created_at: '',
}) as Job)

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('HR activity filters', () => {
  it('uses server-normalized activity for the local confirmation list', () => {
    expect(filterJobs(jobs, EMPTY_JOB_FILTERS)).toHaveLength(6)
    expect(filterJobs(jobs, { ...EMPTY_JOB_FILTERS, hrActiveWithin: '3d' }).map(job => job.id)).toEqual(['0', '1', '2'])
    expect(filterJobs(jobs, { ...EMPTY_JOB_FILTERS, hrActiveWithin: 'unknown' }).map(job => job.id)).toEqual(['5'])
    expect(filterJobs([{ id: 'legacy' } as Job], { ...EMPTY_JOB_FILTERS, hrActiveWithin: '7d' })).toEqual([])
  })

  it('offers activity and unknown choices with an explicit snapshot caveat', () => {
    const onChange = vi.fn()
    const onReset = vi.fn()
    render(<JobFilterBar filters={{ ...EMPTY_JOB_FILTERS, hrActiveWithin: '3d' }} onChange={onChange}
      onReset={onReset} resultCount={3} totalCount={6} />)
    fireEvent.change(screen.getByRole('combobox', { name: '招聘者活跃时间' }), { target: { value: 'unknown' } })
    expect(onChange).toHaveBeenCalledWith({ ...EMPTY_JOB_FILTERS, hrActiveWithin: 'unknown' })
    expect(screen.getByText(/按采集时记录的 HR 活跃状态筛选/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '重置筛选' }))
    expect(onReset).toHaveBeenCalledOnce()
  })

  it('refetches the server selection when activity changes and clears the parameter on reset', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items: [], total: 0, all_total: 6 }) })
    vi.stubGlobal('fetch', fetchMock)
    const { result, rerender } = renderHook(({ activity }) => useJobSearch({ ...EMPTY_JOB_FILTERS, hrActiveWithin: activity }, 0, 15), {
      initialProps: { activity: '3d' },
    })
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(String(fetchMock.mock.calls[0][0])).toContain('hr_active_within=3d')
    rerender({ activity: 'unknown' })
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(String(fetchMock.mock.calls[1][0])).toContain('hr_active_within=unknown')
    rerender({ activity: '' })
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3))
    expect(String(fetchMock.mock.calls[2][0])).not.toContain('hr_active_within')
  })
})
