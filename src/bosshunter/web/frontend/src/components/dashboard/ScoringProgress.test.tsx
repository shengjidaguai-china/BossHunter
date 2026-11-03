import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { ScoringProgress } from './ScoringProgress'

afterEach(cleanup)

describe('ScoringProgress', () => {
  it('counts filtered and failed jobs as processed, and clamps invalid counters', () => {
    const { rerender } = render(<ScoringProgress status="running" metrics={{ ai_total: 3, ai_completed: 2, ai_passed: 1, ai_failed: 1 }} />)
    expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('66')
    expect(screen.getByText('已处理 2 / 3 · 66%')).toBeTruthy()
    expect(screen.getByText('失败 1')).toBeTruthy()
    rerender(<ScoringProgress status="completed" metrics={{ ai_total: 3, ai_completed: 9, ai_filtered: -1 }} />)
    expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('100')
    expect(screen.getByText('过滤 0')).toBeTruthy()
  })

  it('keeps preparation indeterminate and never shows a fabricated percentage', () => {
    render(<ScoringProgress status="running" metrics={{ ai_total: NaN, ai_completed: Infinity }} />)
    expect(screen.getByRole('progressbar').hasAttribute('aria-valuenow')).toBe(false)
    expect(screen.getByText('正在准备待评分岗位…')).toBeTruthy()
  })

  it('does not show a waiting animation for an ended run without counters', () => {
    render(<ScoringProgress status="stopped" />)
    expect(screen.getByText('暂无评分计数')).toBeTruthy()
    expect(screen.queryByText('正在准备待评分岗位…')).toBeNull()
  })

  it('preserves partial progress while paused and starts a resumed batch at zero', () => {
    const { rerender } = render(<ScoringProgress status="paused" metrics={{ ai_total: 10, ai_completed: 4 }} />)
    expect(screen.getByRole('progressbar').getAttribute('aria-valuetext')).toContain('已暂停，已处理 4 / 10')
    rerender(<ScoringProgress status="running" metrics={{ ai_total: 6, ai_completed: 0 }} />)
    expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('0')
    expect(screen.getByText('已处理 0 / 6 · 0%')).toBeTruthy()
  })

  it.each(['failed', 'stopped', 'completed_with_errors'])('retains actual counters when %s', status => {
    render(<ScoringProgress status={status} metrics={{ ai_total: 10, ai_completed: 4 }} />)
    expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('40')
    expect(screen.getByRole('progressbar').getAttribute('aria-valuetext')).not.toContain('评分中')
  })
})
