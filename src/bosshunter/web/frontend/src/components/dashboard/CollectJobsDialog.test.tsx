import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { CollectJobsDialog } from './CollectJobsDialog'

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    const data = url === '/api/config' ? { search: { keywords: ['AI'], cities: ['北京', '上海'] } }
      : url.startsWith('/api/collection/runs') ? [] : { ok: true, cities: [] }
    return new Response(JSON.stringify(data), { status: 200 })
  }))
})
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

it('submits the city policy and only enables an eight hour session when explicitly selected', async () => {
  const start = vi.fn(async (_options: Record<string, unknown>) => ({ ok: true }))
  const close = vi.fn()
  render(<CollectJobsDialog open activeTask={null} onClose={close} onStart={start} />)
  await screen.findByDisplayValue('AI')
  expect(screen.getByRole('switch', { name: '持续采集' }).getAttribute('aria-checked')).toBe('false')
  fireEvent.click(screen.getByRole('switch', { name: '持续采集' }))
  expect((screen.getByLabelText('会话最长时长（小时）') as HTMLInputElement).value).toBe('8')
  fireEvent.click(screen.getByRole('button', { name: '重新采集' }))
  await waitFor(() => expect(start).toHaveBeenCalledTimes(1))
  expect(start.mock.calls[0][0]).toMatchObject({
    platform_order: ['boss'], continuous_collection: { enabled: true, max_duration_hours: 8 },
    platforms: { boss: { cities: ['北京', '上海'], city_yield_policy: { enabled: true, warmup_minutes: 10, window_minutes: 5, min_new_jobs: 5 } } },
  })
  expect(close).toHaveBeenCalled()
})

it('full workflow hides continuous collection and submits the existing scoring behavior', async () => {
  const start = vi.fn(async (_options: Record<string, unknown>) => ({ ok: true }))
  render(<CollectJobsDialog open mode="full" activeTask={null} onClose={vi.fn()} onStart={start} />)
  await screen.findByDisplayValue('AI')
  expect(screen.queryByRole('switch', { name: '持续采集' })).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: '开始全流程' }))
  await waitFor(() => expect(start).toHaveBeenCalledTimes(1))
  expect(start.mock.calls[0][0].auto_score).toBe(true)
  expect(start.mock.calls[0][0].continuous_collection).toBeUndefined()
})
