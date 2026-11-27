import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Sidebar } from './Sidebar'

afterEach(cleanup)

describe('Sidebar', () => {
  it('keeps navigation and GitHub accessible when collapsed and expands from the logo', () => {
    const onToggle = vi.fn()
    const onNavigate = vi.fn()
    render(
      <MemoryRouter>
        <Sidebar collapsed pendingReplies={2} onToggle={onToggle} onNavigate={onNavigate} />
      </MemoryRouter>,
    )
    fireEvent.click(screen.getByRole('button', { name: '展开导航' }))
    expect(onToggle).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('link', { name: '岗位池' }))
    expect(onNavigate).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('link', { name: 'BossHunter GitHub' }).querySelector('svg')).not.toBeNull()
    expect(screen.getByLabelText('有待处理事项')).not.toBeNull()
  })

  it('provides a collapse button in the expanded navigation', () => {
    const onToggle = vi.fn()
    render(<MemoryRouter><Sidebar pendingReplies={0} onToggle={onToggle} /></MemoryRouter>)
    fireEvent.click(screen.getByRole('button', { name: '收起导航' }))
    expect(onToggle).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('button', { name: '收起导航' }).getAttribute('aria-expanded')).toBe('true')
  })
})
