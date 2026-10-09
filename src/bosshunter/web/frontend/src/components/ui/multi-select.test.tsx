import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MultiSelect } from './multi-select'

const options = [
  { value: 'ready', label: '待确认' },
  { value: 'filtered', label: '已过滤' },
  { value: 'skipped', label: '已跳过' },
]

describe('MultiSelect', () => {
  afterEach(cleanup)

  it('shows selected labels instead of only a count', () => {
    render(<MultiSelect value={['ready', 'filtered']} options={options} placeholder="全部状态" onChange={vi.fn()} />)

    expect(screen.getByText('待确认、已过滤')).toBeTruthy()
  })

  it('supports select-all and clear actions', () => {
    const onChange = vi.fn()
    render(<MultiSelect value={['ready']} options={options} placeholder="全部状态" onChange={onChange} />)

    fireEvent.click(screen.getByRole('checkbox', { name: '全选' }))
    expect(onChange).toHaveBeenCalledWith(['ready', 'filtered', 'skipped'])
    fireEvent.click(screen.getByRole('button', { name: '清空' }))
    expect(onChange).toHaveBeenLastCalledWith([])
  })

  it('closes an open filter with Escape and returns focus to its trigger', () => {
    render(<MultiSelect value={[]} options={options} placeholder="全部状态" onChange={vi.fn()} />)
    const trigger = screen.getByText('全部状态').closest('summary')!
    const details = trigger.closest('details')!

    fireEvent.click(trigger)
    expect(details.open).toBe(true)

    fireEvent.keyDown(document, { key: 'Escape' })
    expect(details.open).toBe(false)
    expect(document.activeElement).toBe(trigger)
  })

  it('closes an open filter when clicking outside', () => {
    render(<><MultiSelect value={[]} options={options} placeholder="全部状态" onChange={vi.fn()} /><button>外部区域</button></>)
    const trigger = screen.getByText('全部状态').closest('summary')!
    const details = trigger.closest('details')!

    fireEvent.click(trigger)
    expect(details.open).toBe(true)

    fireEvent.pointerDown(screen.getByRole('button', { name: '外部区域' }))
    expect(details.open).toBe(false)
  })

  it('labels its checkbox group for assistive technology', () => {
    render(<MultiSelect value={[]} options={options} placeholder="全部状态" onChange={vi.fn()} />)
    fireEvent.click(screen.getByText('全部状态').closest('summary')!)

    expect(screen.getByRole('group', { name: '全部状态选项' })).toBeTruthy()
  })
})
