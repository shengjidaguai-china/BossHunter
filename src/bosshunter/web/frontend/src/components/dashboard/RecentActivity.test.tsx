import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { RecentActivity } from './RecentActivity'
import type { HistoryItem } from '@/hooks/useDashboard'

function buildHistoryItem(id: number, overrides: Partial<HistoryItem> = {}): HistoryItem {
  return {
    id,
    job_id: `job-${id}`,
    action: 'scored',
    detail: '',
    created_at: '2026-11-24 10:00:00',
    company: `公司${id}`,
    title: `岗位${id}`,
    ...overrides,
  }
}

describe('RecentActivity', () => {
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('hides collapse toggle and mark-read button when empty, and hides toggle for a single row', () => {
    const onMarkAllRead = vi.fn()
    const { rerender } = render(<RecentActivity data={[]} onMarkAllRead={onMarkAllRead} />)
    expect(screen.getByText('暂无未读活动')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /折叠|展开/ })).toBeNull()
    expect(screen.queryByRole('button', { name: '一键已读' })).toBeNull()

    rerender(<RecentActivity data={[buildHistoryItem(1)]} onMarkAllRead={onMarkAllRead} />)
    expect(screen.getByText('公司1 · 岗位1')).toBeTruthy()
    expect(screen.getByRole('button', { name: '一键已读' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: /折叠|展开/ })).toBeNull()
  })

  it('collapses to one row and expands back when more than one item exists', () => {
    const items = [buildHistoryItem(1), buildHistoryItem(2), buildHistoryItem(3)]
    const { container } = render(<RecentActivity data={items} onMarkAllRead={vi.fn()} />)

    const toggle = screen.getByRole('button', { name: '折叠最近活动' })
    expect(toggle.getAttribute('aria-expanded')).toBe('true')
    const controlsId = toggle.getAttribute('aria-controls') || ''
    const overflow = container.querySelector(`[id="${controlsId}"]`)
    expect(overflow?.hasAttribute('hidden')).toBe(false)

    fireEvent.click(toggle)
    const expandToggle = screen.getByRole('button', { name: '展开最近活动' })
    expect(expandToggle.getAttribute('aria-expanded')).toBe('false')
    expect(overflow?.hasAttribute('hidden')).toBe(true)
    expect(screen.getByText('公司1 · 岗位1').closest('[hidden]')).toBeNull()
    expect(screen.getByText('公司2 · 岗位2').closest('[hidden]')).toBe(overflow)

    fireEvent.click(expandToggle)
    expect(screen.getByRole('button', { name: '折叠最近活动' }).getAttribute('aria-expanded')).toBe('true')
    expect(overflow?.hasAttribute('hidden')).toBe(false)
  })

  it('invokes mark-all-read callback when 一键已读 is clicked', async () => {
    const onMarkAllRead = vi.fn().mockResolvedValue(undefined)
    render(<RecentActivity data={[buildHistoryItem(1), buildHistoryItem(2)]} onMarkAllRead={onMarkAllRead} />)
    fireEvent.click(screen.getByRole('button', { name: '一键已读' }))
    await waitFor(() => expect(onMarkAllRead).toHaveBeenCalledTimes(1))
  })
})
