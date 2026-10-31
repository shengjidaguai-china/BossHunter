import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import DashboardPage from './DashboardPage'
afterEach(() => { cleanup(); vi.unstubAllGlobals() })
it.each([true, false])('unifies three-platform delivery with explicit confirmation (confirmed=%s)', async confirmed => {
  const jobs = ['zhilian', '51job', 'liepin'].map(id => ({ id, company: id, title: '工程师', status: 'ready', score: 90, source_platform: id }))
  const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
    const url = String(input)
    const body = url.startsWith('/api/jobs/search') ? { items: jobs, total: 3, all_total: 3 }
      : url === '/api/workbench' ? { pending_confirmation: [], pending_greetings: [], send_errors: [], needs_resume: [], funnel: {}, funnel_today: {}, task: null, last_task: null }
      : url === '/api/workbench/deliver' ? { queued_count: 3 } : []
    return new Response(JSON.stringify(body), { status: 200 })
  })
  const confirm = vi.fn((_message: string) => confirmed)
  vi.stubGlobal('fetch', fetchMock)
  vi.stubGlobal('confirm', confirm)
  render(<DashboardPage view="jobs" />)
  for (const job of jobs) fireEvent.click(await screen.findByRole('checkbox', { name: `选择 ${job.company} 工程师` }))
  fireEvent.click(screen.getByRole('button', { name: '一键投递已选' }))
  expect(confirm).toHaveBeenCalledOnce()
  for (const text of ['网站默认简历', '选择简历', '问卷', '验证码', '无法核实结果', '不能保证防封号', '全流程仍仅支持 BOSS']) expect(confirm.mock.calls[0]?.[0]).toContain(text)
  const deliveries = () => fetchMock.mock.calls.filter(([url, init]) => url === '/api/workbench/deliver' && init?.method === 'POST')
  if (confirmed) {
    await waitFor(() => expect(deliveries()).toHaveLength(1))
    expect(JSON.parse(String(deliveries()[0][1]?.body))).toEqual({ job_ids: ['zhilian', '51job', 'liepin'] })
  } else expect(deliveries()).toHaveLength(0)
  expect(fetchMock.mock.calls.filter(([url, init]) => init?.method === 'POST' && url !== '/api/workbench/deliver')).toHaveLength(0)
})
