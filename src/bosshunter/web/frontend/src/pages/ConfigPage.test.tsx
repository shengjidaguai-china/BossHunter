import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import ConfigPage from './ConfigPage'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

it('saves fixed greeting mode and restores it when the settings page is reopened', async () => {
  let saved: Record<string, any> = { profile: { greeting_preference: '不要问问题' } }
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    let body: unknown = {}
    if (url === '/api/config') {
      if (init?.method === 'POST') {
        saved = JSON.parse(String(init.body))
        body = { success: true }
      } else body = saved
    }
    if (url.startsWith('/api/cities')) body = { cities: [] }
    return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } })
  })
  vi.stubGlobal('fetch', fetchMock)
  const page = render(<ConfigPage />)
  const toggle = await screen.findByRole('switch', { name: 'AI 生成招呼语' })
  expect(toggle.getAttribute('aria-checked')).toBe('true')
  fireEvent.click(toggle)
  const fixed = '您好，我做过品牌内容，也独立运营过账号。想了解这个岗位。'
  fireEvent.change(screen.getByRole('textbox', { name: '固定招呼语' }), { target: { value: fixed } })
  fireEvent.click(screen.getByRole('button', { name: '保存' }))
  await waitFor(() => expect(saved.profile.ai_greeting_enabled).toBe(false))
  await screen.findByText('配置已保存')
  expect(saved.profile.fixed_greeting).toBe(fixed)
  expect(saved.profile.greeting_preference).toBe('不要问问题')
  page.unmount()
  render(<ConfigPage />)
  expect((await screen.findByRole('textbox', { name: '固定招呼语' }) as HTMLTextAreaElement).value).toBe(fixed)
  fireEvent.click(screen.getByRole('switch', { name: 'AI 生成招呼语' }))
  expect(screen.queryByRole('textbox', { name: '固定招呼语' })).toBeNull()
  fireEvent.click(screen.getByRole('switch', { name: 'AI 生成招呼语' }))
  expect((screen.getByRole('textbox', { name: '固定招呼语' }) as HTMLTextAreaElement).value).toBe(fixed)
})

it('defaults optimization off and disabling unknown salary filtering follows internship selection', async () => {
  let saved: Record<string, any> = { profile: { allow_internship: false, filter_unparsed_salary: true } }
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    let body: unknown = {}
    if (url === '/api/config') {
      if (init?.method === 'POST') { saved = JSON.parse(String(init.body)); body = { success: true } }
      else body = saved
    }
    if (url.startsWith('/api/cities')) body = { cities: [] }
    return new Response(JSON.stringify(body), { status: 200 })
  }))
  render(<ConfigPage />)
  const internship = await screen.findByRole('switch', { name: '接受实习/管培岗位' })
  const filter = screen.getByRole('switch', { name: '过滤面议/无法解析薪资' })
  expect(filter.getAttribute('aria-checked')).toBe('true')
  fireEvent.click(screen.getByRole('button', { name: 'AI 设置' }))
  expect(screen.getByRole('switch', { name: '招呼语质量提醒' }).getAttribute('aria-checked')).toBe('false')
  expect(screen.queryByText('自动采用优化版')).toBeNull()
  fireEvent.click(internship)
  expect(filter.getAttribute('aria-checked')).toBe('false')
  expect((filter as HTMLButtonElement).disabled).toBe(true)
  fireEvent.click(screen.getByRole('button', { name: '保存' }))
  await screen.findByText('配置已保存')
  expect(saved.profile.allow_internship).toBe(true)
  expect(saved.profile.filter_unparsed_salary).toBe(false)
  fireEvent.click(screen.getByRole('switch', { name: '接受实习/管培岗位' }))
  expect((screen.getByRole('switch', { name: '过滤面议/无法解析薪资' }) as HTMLButtonElement).disabled).toBe(false)
  expect(screen.getByRole('switch', { name: '过滤面议/无法解析薪资' }).getAttribute('aria-checked')).toBe('false')
})
