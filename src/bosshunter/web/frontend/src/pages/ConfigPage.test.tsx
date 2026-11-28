import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import ConfigPage from './ConfigPage'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

it('loads provider choices from the backend and accepts a provider absent from frontend code', async () => {
  let saved: Record<string, any> = { ai: { service: 'anthropic', provider: 'anthropic', model: 'old-model' } }
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    let body: unknown = {}
    if (url === '/api/config/schema') body = { ai_services: {
      future_vendor: { label: '新增模型服务商', provider: 'openai_compatible', base_url: 'https://future.example/v1',
        key_env: 'FUTURE_API_KEY', auth_mode: 'api_key', token_limit_field: 'max_completion_tokens', default_model: '' },
    } }
    if (url === '/api/config') {
      if (init?.method === 'POST') { saved = JSON.parse(String(init.body)); body = { success: true } }
      else body = saved
    }
    return new Response(JSON.stringify(body), { status: 200 })
  }))
  render(<ConfigPage />)
  fireEvent.click(await screen.findByRole('button', { name: 'AI 设置' }))
  expect(screen.getByRole('option', { name: '新增模型服务商' })).toBeTruthy()
  fireEvent.change(screen.getByLabelText('AI 服务商'), { target: { value: 'future_vendor' } })
  expect((screen.getByLabelText('Base URL') as HTMLInputElement).value).toBe('https://future.example/v1')
  expect((screen.getByLabelText('模型名称') as HTMLInputElement).value).toBe('')
  expect((screen.getByLabelText('输出 Token 参数') as HTMLSelectElement).value).toBe('max_completion_tokens')
  fireEvent.change(screen.getByLabelText('模型名称'), { target: { value: 'Vendor/Case-Sensitive' } })
  fireEvent.click(screen.getByRole('button', { name: '保存' }))
  await screen.findByText('配置已保存')
  expect(saved.ai.service).toBe('future_vendor')
  expect(saved.ai.model).toBe('Vendor/Case-Sensitive')
  expect(saved.ai.provider).toBe('openai_compatible')
})

it('discovers keyless remote models and lets a deployment enable API authentication', async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    const body = url === '/api/config' ? { ai: { service: 'ollama', provider: 'openai_compatible', auth_mode: 'none',
      base_url: 'http://192.0.2.22:11434/v1', model: 'team/model' } }
      : url === '/api/config/schema' ? { ai_services: { ollama: { label: 'Ollama（本地或远程）', provider: 'openai_compatible',
        base_url: 'http://127.0.0.1:11434/v1', key_env: 'OLLAMA_API_KEY', auth_mode: 'none' } } }
      : url === '/api/config/models' ? { models: ['team/model', 'team/another'] } : {}
    return new Response(JSON.stringify(body), { status: 200 })
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<ConfigPage />)
  fireEvent.click(await screen.findByRole('button', { name: 'AI 设置' }))
  expect(screen.queryByText('API Key', { selector: 'label' })).toBeNull()
  expect((screen.getByLabelText('Base URL') as HTMLInputElement).value).toBe('http://192.0.2.22:11434/v1')
  fireEvent.click(screen.getByRole('button', { name: '获取模型列表' }))
  await screen.findByRole('option', { name: 'team/another' })
  fireEvent.change(screen.getByLabelText('认证方式'), { target: { value: 'api_key' } })
  expect(screen.getByText('API Key', { selector: 'label' })).toBeTruthy()
})

it('saves a custom Anthropic service without forcing it back to OpenAI protocol', async () => {
  let saved: Record<string, any> = { ai: { service: 'custom', provider: 'openai_compatible', auth_mode: 'none',
    model: 'vendor/model', base_url: 'https://gateway.example' } }
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    let body: unknown = {}
    if (String(input) === '/api/config') {
      if (init?.method === 'POST') { saved = JSON.parse(String(init.body)); body = { success: true } }
      else body = saved
    }
    return new Response(JSON.stringify(body), { status: 200 })
  }))
  render(<ConfigPage />)
  fireEvent.click(await screen.findByRole('button', { name: 'AI 设置' }))
  fireEvent.change(screen.getByLabelText('接口协议'), { target: { value: 'anthropic' } })
  expect((screen.getByLabelText('认证方式') as HTMLSelectElement).value).toBe('api_key')
  fireEvent.click(screen.getByRole('button', { name: '保存' }))
  await screen.findByText('配置已保存')
  expect(saved.ai.provider).toBe('anthropic')
})

it('requires saving before local AI authorization and supports revocation without exposing API fields', async () => {
  let saved: Record<string, any> = { ai: { service: 'anthropic', provider: 'anthropic', model: 'api-model' } }
  let finishAuthorization: () => void = () => {}
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
    if (url === '/api/config/local-ai/authorize') {
      await new Promise<void>(resolve => { finishAuthorization = resolve })
      body = { success: true, message: '本机 AI 已验证并授权' }
    }
    if (url === '/api/config/local-ai/revoke') body = { success: true, message: '本机 AI 授权已撤销' }
    return new Response(JSON.stringify(body), { status: 200 })
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<ConfigPage />)
  fireEvent.click(await screen.findByRole('button', { name: 'AI 设置' }))
  fireEvent.change(screen.getByLabelText('AI 服务商'), { target: { value: 'codex_cli' } })
  expect(screen.queryByText('API Key', { selector: 'label' })).toBeNull()
  expect(screen.queryByRole('button', { name: '获取模型列表' })).toBeNull()
  expect((screen.getByRole('button', { name: '验证并授权' }) as HTMLButtonElement).disabled).toBe(true)
  fireEvent.click(screen.getByRole('button', { name: '保存' }))
  await screen.findByText('配置已保存')
  expect(saved.ai.provider).toBe('local_cli')
  expect(saved.ai.model).toBe('')
  fireEvent.click(screen.getByRole('button', { name: '验证并授权' }))
  await screen.findByRole('button', { name: '处理中…' })
  expect(screen.getByRole('button', { name: '重置' }).matches(':disabled')).toBe(true)
  expect(screen.getByRole('button', { name: '保存' }).matches(':disabled')).toBe(true)
  expect(screen.getByLabelText('模型名称').matches(':disabled')).toBe(true)
  finishAuthorization()
  await screen.findByText('本机 AI 已验证并授权')
  expect(screen.getByRole('button', { name: '重置' }).matches(':disabled')).toBe(false)
  expect(fetchMock.mock.calls.find(([input]) => String(input).endsWith('/authorize'))?.[1]?.body).toBe('{"confirm":true}')
  fireEvent.click(screen.getByRole('button', { name: '撤销授权' }))
  await screen.findByText('本机 AI 授权已撤销')
  expect((screen.getByRole('button', { name: '撤销授权' }) as HTMLButtonElement).disabled).toBe(true)
})

it('keeps local AI unauthorized after verification fails', async () => {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    const body = url === '/api/config' ? { ai: { service: 'claude_cli', provider: 'local_cli', model: '' } }
      : url.endsWith('/authorize') ? { error: '请先登录 Claude Code' } : {}
    return new Response(JSON.stringify(body), { status: url.endsWith('/authorize') ? 400 : 200 })
  }))
  render(<ConfigPage />)
  fireEvent.click(await screen.findByRole('button', { name: 'AI 设置' }))
  fireEvent.click(screen.getByRole('button', { name: '验证并授权' }))
  await screen.findByText('请先登录 Claude Code')
  expect((screen.getByRole('button', { name: '撤销授权' }) as HTMLButtonElement).disabled).toBe(true)
})

it('blocks invalid windows, saves multiple periods and reloads their exact times', async () => {
  let saved: Record<string, any> = { throttle: { send_windows: ['09:00-12:00'] } }
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    let body: unknown = {}
    if (String(input) === '/api/config') {
      if (init?.method === 'POST') { saved = JSON.parse(String(init.body)); body = { success: true } }
      else body = saved
    }
    if (String(input).startsWith('/api/cities')) body = { cities: [] }
    return new Response(JSON.stringify(body), { status: 200 })
  })
  vi.stubGlobal('fetch', fetchMock)
  const view = render(<ConfigPage />)
  fireEvent.click(await screen.findByRole('button', { name: '反监测设置' }))
  fireEvent.click(screen.getByRole('button', { name: '添加时间段' }))
  expect(screen.getByRole('button', { name: '保存' }).getAttribute('data-tour')).toBe('config-save')
  expect((screen.getByRole('button', { name: '保存' }) as HTMLButtonElement).disabled).toBe(true)
  fireEvent.change(screen.getByLabelText('时间段 2 开始时间'), { target: { value: '11:00' } })
  fireEvent.change(screen.getByLabelText('时间段 2 结束时间'), { target: { value: '16:00' } })
  expect(screen.getByRole('alert').textContent).toContain('重叠')
  expect((screen.getByRole('button', { name: '保存' }) as HTMLButtonElement).disabled).toBe(true)
  fireEvent.change(screen.getByLabelText('时间段 2 开始时间'), { target: { value: '14:00' } })
  fireEvent.change(screen.getByLabelText('时间段 1 结束时间'), { target: { value: '11:30' } })
  fireEvent.click(screen.getByRole('button', { name: '保存' }))
  await screen.findByText('配置已保存')
  expect(saved.throttle.send_windows).toEqual(['09:00-11:30', '14:00-16:00'])
  expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'POST')).toHaveLength(1)
  view.unmount()
  render(<ConfigPage />)
  fireEvent.click(await screen.findByRole('button', { name: '反监测设置' }))
  expect((screen.getByLabelText('时间段 1 结束时间') as HTMLInputElement).value).toBe('11:30')
  expect((screen.getByLabelText('时间段 2 开始时间') as HTMLInputElement).value).toBe('14:00')
  fireEvent.click(screen.getByRole('button', { name: '删除时间段 2' }))
  fireEvent.click(screen.getByRole('button', { name: '保存' }))
  await screen.findByText('配置已保存')
  expect(saved.throttle.send_windows).toEqual(['09:00-11:30'])
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

it('points the guide at the enabled search platform when BOSS is off', async () => {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    const body = url === '/api/config'
      ? { platforms: { boss: { enabled: false }, zhilian: { enabled: true, search: {} } } }
      : url.startsWith('/api/cities') ? { cities: [] } : {}
    return new Response(JSON.stringify(body), { status: 200 })
  }))
  render(<ConfigPage />)

  const keyword = await screen.findByPlaceholderText('如：人力、产品运营')
  const city = screen.getByPlaceholderText('如：深圳')
  expect(document.querySelector('[data-tour="search-keywords"]')?.contains(keyword)).toBe(true)
  expect(document.querySelector('[data-tour="search-city"]')?.contains(city)).toBe(true)
})

it('points the guide at the platform switch when no search platform is enabled', async () => {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    const body = url === '/api/config'
      ? { platforms: Object.fromEntries(['boss', 'zhilian', '51job', 'liepin'].map(platform => [platform, { enabled: false }])) }
      : url.startsWith('/api/cities') ? { cities: [] } : {}
    return new Response(JSON.stringify(body), { status: 200 })
  }))
  render(<ConfigPage />)

  const bossSwitch = await screen.findByRole('checkbox', { name: 'BOSS 直聘' })
  expect(document.querySelector('[data-tour="search-keywords"]')?.contains(bossSwitch)).toBe(true)
  expect(document.querySelector('[data-tour="search-city"]')?.contains(bossSwitch)).toBe(true)
})
