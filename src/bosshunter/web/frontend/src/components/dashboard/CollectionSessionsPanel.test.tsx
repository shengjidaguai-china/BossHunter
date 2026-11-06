import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { CollectionSessionsPanel } from './CollectionSessionsPanel'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

it('restores the overnight summary and persists manual continue and stop actions', async () => {
  const session = { id: 'night', status: 'running', collected_job_ids: ['one', 'two'], city_totals: { 北京: 2 },
    state: { phase: 'waiting_user', round: 3, manual_pending_reason: 'captcha',
      started_at: '2026-10-26T12:00:00Z', deadline_at: '2026-10-26T20:00:00Z', phase_seconds: { collecting: 600, waiting_round: 900 } } }
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url.endsWith('/continue') && init?.method === 'POST') session.state.phase = 'collecting'
    if (url.endsWith('/stop') && init?.method === 'POST') session.status = 'stopped'
    return new Response(JSON.stringify(init?.method === 'POST' ? { ok: true } : [session]), { status: 200 })
  })
  vi.stubGlobal('fetch', fetchMock)
  const panel = render(<CollectionSessionsPanel />)
  await screen.findByText('待处理：需要完成验证码')
  expect(screen.getByText('北京 2')).toBeTruthy()
  expect(screen.getByText(/采集 10 分钟 · 等待 15 分钟/)).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '继续采集' }))
  await waitFor(() => expect(screen.queryByRole('button', { name: '继续采集' })).toBeNull())
  fireEvent.click(screen.getByRole('button', { name: '停止全部' }))
  await waitFor(() => expect(screen.queryByRole('button', { name: '停止全部' })).toBeNull())
  panel.unmount()
  render(<CollectionSessionsPanel />)
  await screen.findByText('北京 2')
  expect(fetchMock).toHaveBeenCalledWith('/api/collection/sessions/night/continue', { method: 'POST' })
  expect(fetchMock).toHaveBeenCalledWith('/api/collection/sessions/night/stop', { method: 'POST' })
})

it('keeps a failed action visible and available for retry', async () => {
  vi.stubGlobal('fetch', vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => new Response(JSON.stringify(init?.method === 'POST'
    ? { error: '会话已结束或不存在' }
    : [{ id: 'night', status: 'running', collected_job_ids: [], city_totals: {}, state: { phase: 'collecting', round: 1, started_at: '', deadline_at: '' } }]), { status: init?.method === 'POST' ? 400 : 200 })))
  render(<CollectionSessionsPanel />)
  fireEvent.click(await screen.findByRole('button', { name: '停止全部' }))
  await screen.findByText('会话已结束或不存在')
  expect((screen.getByRole('button', { name: '停止全部' }) as HTMLButtonElement).disabled).toBe(false)
})
