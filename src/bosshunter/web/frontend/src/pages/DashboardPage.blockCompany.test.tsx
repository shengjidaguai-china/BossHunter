import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import DashboardPage from './DashboardPage'

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

describe('岗位列表屏蔽公司', () => {
  let rules: string[]
  let company: string
  let applyError: string
  let previewError: string
  const confirm = vi.fn(() => true)
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url === '/api/agent/state') {
      return jsonResponse({ preferences: { blocked_companies: [...rules] } })
    }
    if (url === '/api/agent/config/preview') {
      if (previewError) return jsonResponse({ error: previewError }, 400)
      return jsonResponse({ preferences: JSON.parse(String(init?.body)).preferences, requires_confirmation: true })
    }
    if (url === '/api/agent/config/apply') {
      if (applyError) return jsonResponse({ error: applyError }, 409)
      rules = JSON.parse(String(init?.body)).preferences.blocked_companies
      return jsonResponse({ success: true, preferences: { blocked_companies: rules } })
    }
    if (url.startsWith('/api/jobs/search')) {
      const blocked = rules.some(rule => rule.trim() && company.toLowerCase().includes(rule.trim().toLowerCase()))
      const items = blocked ? [] : [{ id: 'job-1', company, title: '前端工程师', status: 'ready', score: 90, created_at: '' }]
      return jsonResponse({
        items, total: items.length, all_total: items.length,
      })
    }
    if (url === '/api/workbench') {
      return jsonResponse({
        funnel: {}, funnel_today: {}, pending_confirmation: [], pending_greetings: [],
        send_errors: [], needs_resume: [], task: null, last_task: null,
        send_quota: { daily_limit: 30, sent: 0, remaining: 30, exhausted: false },
      })
    }
    return jsonResponse([])
  })

  const requestsTo = (path: string) => fetchMock.mock.calls.filter(([url]) => String(url) === path)

  beforeEach(() => {
    rules = ['已有屏蔽公司']
    company = '测试科技'
    applyError = ''
    previewError = ''
    fetchMock.mockClear()
    confirm.mockReset().mockReturnValue(true)
    vi.stubGlobal('fetch', fetchMock)
    vi.stubGlobal('confirm', confirm)
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  async function clickBlock() {
    render(<DashboardPage view="jobs" />)
    const button = await screen.findByRole('button', { name: `屏蔽公司 ${company || '公司名缺失'}` })
    fireEvent.click(button)
    return button as HTMLButtonElement
  }

  it('previews before confirmation and changes only the company list while preserving existing rules', async () => {
    confirm.mockImplementation(() => {
      expect(requestsTo('/api/agent/config/preview')).toHaveLength(1)
      expect(requestsTo('/api/agent/config/apply')).toHaveLength(0)
      return true
    })
    await clickBlock()
    expect(await screen.findByText('已屏蔽“测试科技”，匹配岗位已从列表隐藏，记录保留；解除屏蔽后恢复显示。')).toBeTruthy()
    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('新增屏蔽公司：测试科技'))
    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('已有屏蔽规则：已有屏蔽公司'))
    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('从列表隐藏'))
    expect(JSON.parse(String(requestsTo('/api/agent/config/apply')[0][1]?.body))).toEqual({
      preferences: { blocked_companies: ['已有屏蔽公司', '测试科技'] }, confirm: true,
    })
    await waitFor(() => expect(screen.queryByRole('button', { name: '屏蔽公司 测试科技' })).toBeNull())
    expect(await screen.findByText('没有符合当前条件的岗位')).toBeTruthy()
    expect(screen.queryByText('JD摘要')).toBeNull()
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'POST').map(([url]) => url)).toEqual([
      '/api/agent/config/preview', '/api/agent/config/apply',
    ])
  })

  it('does not save when confirmation is cancelled', async () => {
    confirm.mockReturnValue(false)
    const button = await clickBlock()
    expect(await screen.findByText('已取消屏蔽，配置未修改。')).toBeTruthy()
    expect(requestsTo('/api/agent/config/apply')).toHaveLength(0)
    expect(rules).toEqual(['已有屏蔽公司'])
    expect(button.disabled).toBe(false)
  })

  it('hides jobs matching saved rules on every page mount and restores them when unblocked', async () => {
    rules = ['TEST']
    company = 'test 科技'
    const firstVisit = render(<DashboardPage view="jobs" />)
    expect(await screen.findByText('没有符合当前条件的岗位')).toBeTruthy()
    expect(screen.queryByText(company)).toBeNull()
    firstVisit.unmount()
    render(<DashboardPage view="jobs" />)
    expect(await screen.findByText('没有符合当前条件的岗位')).toBeTruthy()
    expect(screen.queryByText(company)).toBeNull()
    rules = []
    act(() => window.dispatchEvent(new Event('bosshunter-config-saved')))
    expect(await screen.findByRole('button', { name: '屏蔽公司 test 科技' })).toBeTruthy()
    expect(confirm).not.toHaveBeenCalled()
    expect(requestsTo('/api/agent/config/apply')).toHaveLength(0)
  })

  it('clears selected jobs when a saved blacklist hides them', async () => {
    render(<DashboardPage view="jobs" />)
    await screen.findByRole('button', { name: '屏蔽公司 测试科技' })
    fireEvent.click(screen.getByRole('checkbox', { name: '选择 测试科技 前端工程师' }))
    expect(screen.getByText('已选择 1 条')).toBeTruthy()
    rules.push(company)
    act(() => window.dispatchEvent(new Event('bosshunter-config-saved')))
    expect(await screen.findByText('没有符合当前条件的岗位')).toBeTruthy()
    expect(screen.getByText('已选择 0 条')).toBeTruthy()
    expect(requestsTo('/api/agent/config/apply')).toHaveLength(0)
  })

  it('requires a new preview if another page changes the list during confirmation', async () => {
    confirm.mockImplementation(() => {
      rules = ['已有屏蔽公司', '另一个页面新增的公司']
      return true
    })
    await clickBlock()
    expect(await screen.findByText('屏蔽名单已变化，请重新点击“屏蔽公司”查看最新预览。')).toBeTruthy()
    expect(requestsTo('/api/agent/config/apply')).toHaveLength(0)
    expect(rules).toContain('另一个页面新增的公司')
  })

  it('shows the backend error and allows retry when saving is blocked', async () => {
    applyError = '采集任务运行中，请结束后再修改配置'
    const button = await clickBlock()
    expect(await screen.findByText(applyError)).toBeTruthy()
    expect(button.disabled).toBe(false)
    expect(button.textContent).toBe('屏蔽公司')
    expect(rules).toEqual(['已有屏蔽公司'])
  })

  it('does not ask for confirmation or save if preview validation fails', async () => {
    previewError = '公司名超过长度限制'
    await clickBlock()
    expect(await screen.findByText(previewError)).toBeTruthy()
    expect(confirm).not.toHaveBeenCalled()
    expect(requestsTo('/api/agent/config/apply')).toHaveLength(0)
  })

  it('disables blocking when the company name is missing', async () => {
    company = ''
    const button = await clickBlock()
    expect(button.disabled).toBe(true)
    expect(confirm).not.toHaveBeenCalled()
    expect(requestsTo('/api/agent/config/preview')).toHaveLength(0)
  })
})
