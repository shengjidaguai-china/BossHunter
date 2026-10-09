import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { SendWindowsInput, sendWindowsError } from './SendWindowsInput'

afterEach(cleanup)

function Editor() {
  const [windows, setWindows] = useState(['09:00-12:00'])
  return <><SendWindowsInput value={windows} onChange={setWindows} /><output>{JSON.stringify(windows)}</output></>
}

it('adds, edits and deletes windows without changing the YAML representation', () => {
  render(<Editor />)
  fireEvent.click(screen.getByRole('button', { name: '添加时间段' }))
  expect(screen.getByRole('alert').textContent).toContain('开始时间和结束时间')
  fireEvent.change(screen.getByLabelText('时间段 2 开始时间'), { target: { value: '14:00' } })
  fireEvent.change(screen.getByLabelText('时间段 2 结束时间'), { target: { value: '16:00' } })
  expect(screen.queryByRole('alert')).toBeNull()
  fireEvent.change(screen.getByLabelText('时间段 1 结束时间'), { target: { value: '11:30' } })
  expect(screen.getByRole('status').textContent).toBe('["09:00-11:30","14:00-16:00"]')
  fireEvent.click(screen.getByRole('button', { name: '删除时间段 1' }))
  expect((screen.getByLabelText('时间段 1 开始时间') as HTMLInputElement).value).toBe('14:00')
  fireEvent.click(screen.getByRole('button', { name: '删除时间段 1' }))
  expect(screen.getByRole('status').textContent).toBe('[]')
  expect(screen.getByRole('alert').textContent).toContain('不限制发送时间')
})

describe('validates the same boundaries as the backend', () => {
  it.each([
    null, '09:00-16:00', [null], [''], ['9:00-16:00'], ['09:00-24:00'],
    ['09:60-16:00'], ['09:00-09:00'], ['23:00-01:00'],
    ['09:00-12:00', '09:00-12:00'], ['09:00-12:00', '11:00-16:00'],
  ].map(value => [value]))('rejects invalid value %j', value => expect(sendWindowsError(value)).not.toBeNull())
  it.each([[], ['00:00-23:59'], ['12:00-16:00', '09:00-12:00'], [' 09:00 - 16:00 ']].map(value => [value]))(
    'accepts compatible value %j', value => expect(sendWindowsError(value)).toBeNull(),
  )
})
