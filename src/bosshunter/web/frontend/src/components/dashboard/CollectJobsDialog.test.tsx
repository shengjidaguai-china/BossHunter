import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { CollectJobsDialog } from './CollectJobsDialog'
afterEach(() => { cleanup(); vi.unstubAllGlobals() })
it('keeps full workflow BOSS-only even when every platform is configured and enabled', async () => {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => new Response(JSON.stringify(
    String(input) === '/api/config' ? {
      collection: { default_order: ['zhilian', '51job', 'liepin', 'boss'] },
      platforms: Object.fromEntries(['boss', 'zhilian', '51job', 'liepin'].map(platform => [platform, { enabled: true, search: { keywords: ['工程师'], cities: ['上海'] } }])),
    } : { ok: true, cities: [] },
  ), { status: 200 })))
  const onStart = vi.fn(async (_options: Record<string, unknown>) => ({ ok: true }))
  render(<CollectJobsDialog open mode="full" activeTask={null} onClose={() => {}} onStart={onStart} />)
  await screen.findByDisplayValue('工程师')
  for (const name of ['智联招聘', '前程无忧', '猎聘']) {
    const checkbox = screen.getByRole('checkbox', { name }) as HTMLInputElement
    expect(checkbox.disabled).toBe(true)
    expect(checkbox.checked).toBe(false)
  }
  fireEvent.click(screen.getByRole('button', { name: /启动|开始/ }))
  await waitFor(() => expect(onStart).toHaveBeenCalledOnce())
  expect(onStart.mock.calls[0][0]).toMatchObject({ platform_order: ['boss'], platforms: { boss: expect.any(Object) } })
  expect(Object.keys(onStart.mock.calls[0][0].platforms as object)).toEqual(['boss'])
})
