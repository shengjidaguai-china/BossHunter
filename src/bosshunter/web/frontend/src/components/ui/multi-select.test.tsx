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
})
