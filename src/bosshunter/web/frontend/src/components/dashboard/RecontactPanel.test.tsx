import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { RecontactPanel } from './RecontactPanel'

const items = [{ id: 'unreplied-one', company: '测试公司', title: 'AI 实习', greeting: '上次已确认的文案', last_contact_at: '2026-10-19 01:00:00', recontact_count: 0 }]
const response = (data: unknown, status = 200) => new Response(JSON.stringify(
  typeof data === 'object' && data !== null && 'items' in data ? { default_greeting: '配置中的统一招呼语', ...data } : data
), { status, headers: { 'Content-Type': 'application/json' } })

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

describe('RecontactPanel', () => {
  it('shows greeting editing before searching and when no candidates exist', async () => {
    const fetchMock = vi.fn(async () => response({ items: [], total: 0, default_greeting: '页面打开时的配置文案' }))
    vi.stubGlobal('fetch', fetchMock)
    render(<RecontactPanel taskRunning={false} defaultGreeting="页面打开时的配置文案" onStarted={vi.fn()} />)
    const input = screen.getByLabelText('本次招呼语') as HTMLTextAreaElement
    expect(input.value).toBe('页面打开时的配置文案')
    expect(screen.getByRole('button', { name: '修改招呼语' })).toBeTruthy()
    expect(fetchMock).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: '修改招呼语' }))
    fireEvent.change(input, { target: { value: '查找前编辑的文案' } })
    fireEvent.click(screen.getByRole('button', { name: '查找未回复岗位' }))
    await screen.findByText('暂无符合条件的未回复岗位。可以调整间隔后重新查找。')
    expect(input.value).toBe('查找前编辑的文案')
    expect(screen.getByRole('button', { name: '使用配置招呼语' })).toBeTruthy()
    expect((screen.getByRole('button', { name: '再次投递已选 0 个' }) as HTMLButtonElement).disabled).toBe(true)
  })

  it('loads the dashboard greeting without searching and preserves edits when configuration refreshes', () => {
    const view = render(<RecontactPanel taskRunning={false} onStarted={vi.fn()} />)
    view.rerender(<RecontactPanel taskRunning={false} defaultGreeting="工作台加载的配置文案" onStarted={vi.fn()} />)
    const input = screen.getByLabelText('本次招呼语') as HTMLTextAreaElement
    expect(input.value).toBe('工作台加载的配置文案')
    fireEvent.click(screen.getByRole('button', { name: '修改招呼语' }))
    fireEvent.change(input, { target: { value: '保留这份人工草稿' } })
    view.rerender(<RecontactPanel taskRunning={false} defaultGreeting="后台新配置" onStarted={vi.fn()} />)
    expect(input.value).toBe('保留这份人工草稿')
    fireEvent.click(screen.getByRole('button', { name: '使用配置招呼语' }))
    expect(input.value).toBe('后台新配置')
  })

  it('preserves edits across refresh, restores the latest configured greeting and submits the edited text', async () => {
    let configured = '配置文案 A'
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => init?.method === 'POST'
      ? response({ id: 'edited-task', mode: 'recontact', status: 'running' })
      : response({ items, total: 1, default_greeting: configured }))
    vi.stubGlobal('fetch', fetchMock)
    const started = vi.fn()
    render(<RecontactPanel taskRunning={false} onStarted={started} />)
    fireEvent.click(screen.getByRole('button', { name: '查找未回复岗位' }))
    const input = await screen.findByLabelText('本次招呼语') as HTMLTextAreaElement
    fireEvent.click(screen.getByRole('button', { name: '修改招呼语' }))
    expect(input.readOnly).toBe(false)
    fireEvent.change(input, { target: { value: '本次专用文案' } })
    configured = '配置文案 B'
    fireEvent.click(screen.getByRole('button', { name: '查找未回复岗位' }))
    await waitFor(() => expect((screen.getByRole('button', { name: '查找未回复岗位' }) as HTMLButtonElement).disabled).toBe(false))
    expect(input.value).toBe('本次专用文案')
    fireEvent.click(screen.getByRole('button', { name: '使用配置招呼语' }))
    expect(input.value).toBe('配置文案 B')
    expect(input.readOnly).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: '修改招呼语' }))
    fireEvent.change(input, { target: { value: '本次实际提交的文案' } })
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: '再次投递已选 1 个' }))
    const dialog = screen.getByRole('alertdialog')
    expect(dialog.textContent).toContain('本次实际提交的文案')
    fireEvent.click(within(dialog).getByRole('button', { name: '确认再次投递 1 个' }))
    await waitFor(() => expect(started).toHaveBeenCalled())
    const post = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST')
    expect(JSON.parse(String(post?.[1]?.body)).greeting).toBe('本次实际提交的文案')
    expect(configured).toBe('配置文案 B')
  })

  it('blocks missing, cleared and oversized greetings instead of using historic job text', async () => {
    const fetchMock = vi.fn(async () => response({ items, total: 1, default_greeting: '' }))
    vi.stubGlobal('fetch', fetchMock)
    render(<RecontactPanel taskRunning={false} onStarted={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: '查找未回复岗位' }))
    fireEvent.click(await screen.findByRole('checkbox'))
    const input = screen.getByLabelText('本次招呼语') as HTMLTextAreaElement
    const send = screen.getByRole('button', { name: '再次投递已选 1 个' }) as HTMLButtonElement
    expect(send.disabled).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: '修改招呼语' }))
    fireEvent.change(input, { target: { value: '有效的手动文案' } })
    expect(send.disabled).toBe(false)
    fireEvent.change(input, { target: { value: ' ' } })
    expect(send.disabled).toBe(true)
    fireEvent.change(input, { target: { value: '字'.repeat(301) } })
    expect(send.disabled).toBe(true)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(screen.queryByText('上次已确认的文案')).toBeNull()
  })

  it('only starts explicitly selected candidates after confirmation and uses the configured greeting by default', async () => {
    const task = { id: 'recontact-task', mode: 'recontact', status: 'running' }
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => init?.method === 'POST'
      ? response(task) : response({ items, total: 1, min_hours: 48 }))
    vi.stubGlobal('fetch', fetchMock)
    const started = vi.fn()
    render(<RecontactPanel taskRunning={false} onStarted={started} />)
    expect(fetchMock).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: '查找未回复岗位' }))
    fireEvent.click(await screen.findByRole('checkbox', { name: '选择再次投递：测试公司｜AI 实习' }))
    expect((screen.getByLabelText('本次招呼语') as HTMLTextAreaElement).value).toBe('配置中的统一招呼语')
    expect((screen.getByLabelText('本次招呼语') as HTMLTextAreaElement).readOnly).toBe(true)
    expect(screen.queryByText('上次已确认的文案')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: '再次投递已选 1 个' }))
    const confirm = screen.getByRole('alertdialog', { name: '确认再次投递' })
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'POST')).toHaveLength(0)
    fireEvent.click(within(confirm).getByRole('button', { name: '确认再次投递 1 个' }))
    await waitFor(() => expect(started).toHaveBeenCalledWith(task))
    const post = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST')
    expect(JSON.parse(String(post?.[1]?.body))).toEqual({ job_ids: ['unreplied-one'], min_hours: 48, greeting: '配置中的统一招呼语', confirmed: true })
    expect(screen.queryByRole('alertdialog')).toBeNull()
    expect(screen.getByRole('status').textContent).toContain('已提交 1 个岗位')
  })

  it('keeps stale-candidate errors visible and preserves the selected custom message', async () => {
    vi.stubGlobal('fetch', vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => init?.method === 'POST'
      ? response({ error: '该岗位已有 HR 回复，请刷新列表' }, 409) : response({ items, total: 1 })))
    const started = vi.fn()
    render(<RecontactPanel taskRunning={false} onStarted={started} />)
    fireEvent.click(screen.getByRole('button', { name: '查找未回复岗位' }))
    fireEvent.click(await screen.findByRole('button', { name: '全选候选岗位' }))
    fireEvent.click(screen.getByRole('button', { name: '修改招呼语' }))
    fireEvent.change(screen.getByLabelText('本次招呼语'), { target: { value: '仍然关注这个岗位，希望有机会交流。' } })
    fireEvent.click(screen.getByRole('button', { name: '再次投递已选 1 个' }))
    const confirm = screen.getByRole('alertdialog', { name: '确认再次投递' })
    fireEvent.click(within(confirm).getByRole('button', { name: '确认再次投递 1 个' }))
    expect((await within(confirm).findByRole('alert')).textContent).toContain('已有 HR 回复')
    expect((screen.getByLabelText('本次招呼语') as HTMLTextAreaElement).value).toContain('仍然关注')
    expect(started).not.toHaveBeenCalled()
  })

  it('clears stale selections when the cooldown changes and blocks submission during another task', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => response({ items, total: 1 })))
    render(<RecontactPanel taskRunning onStarted={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: '查找未回复岗位' }))
    fireEvent.click(await screen.findByRole('button', { name: '全选候选岗位' }))
    expect((screen.getByRole('button', { name: '再次投递已选 1 个' }) as HTMLButtonElement).disabled).toBe(true)
    fireEvent.change(screen.getByLabelText('最短再次联系间隔（小时）'), { target: { value: '24' } })
    expect(screen.queryByRole('checkbox')).toBeNull()
    expect(screen.queryByRole('button', { name: '再次投递已选 1 个' })).toBeNull()
  })

  it('marks today sent jobs as read-only and never includes them in select-all', async () => {
    const daily = { ...items[0], id: 'today-one', company: '今日公司', sent_today_at: '2026-10-23 01:17:36' }
    vi.stubGlobal('fetch', vi.fn(async () => response({ items, total: 1, sent_today: [daily], sent_today_total: 1 })))
    render(<RecontactPanel taskRunning={false} onStarted={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: '查找未回复岗位' }))
    const today = await screen.findByRole('region', { name: '当日已投递' })
    expect(today.textContent).toContain('今日公司｜AI 实习')
    expect(today.textContent).toContain('当日已投递 1 个')
    expect(within(today).queryByRole('checkbox')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: '全选候选岗位' }))
    expect(screen.getByRole('button', { name: '再次投递已选 1 个' })).toBeTruthy()
    expect(screen.getAllByRole('checkbox')).toHaveLength(1)
  })

  it('refreshes automatically after successful task progress without treating a started task as sent', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ items, total: 1 }))
      .mockResolvedValueOnce(response({ items: [], total: 0, sent_today: [{ ...items[0], sent_today_at: '2026-10-23 01:17:36' }], sent_today_total: 1 }))
    vi.stubGlobal('fetch', fetchMock)
    const started = vi.fn()
    const view = render(<RecontactPanel taskRunning refreshKey="task:running:0" onStarted={started} />)
    fireEvent.click(screen.getByRole('button', { name: '查找未回复岗位' }))
    fireEvent.click(await screen.findByRole('checkbox', { name: '选择再次投递：测试公司｜AI 实习' }))
    expect(screen.queryByRole('region', { name: '当日已投递' })).toBeNull()
    view.rerender(<RecontactPanel taskRunning={false} refreshKey="task:completed:1" onStarted={started} />)
    expect(await screen.findByRole('region', { name: '当日已投递' })).toBeTruthy()
    expect(screen.queryByRole('checkbox')).toBeNull()
    expect(screen.queryByRole('button', { name: '再次投递已选 1 个' })).toBeNull()
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(started).not.toHaveBeenCalled()
  })

  it('does not restore a sent candidate when an older lookup returns after the daily refresh', async () => {
    let resolveOld!: (value: Response) => void
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ items, total: 1 }))
      .mockImplementationOnce(() => new Promise<Response>(resolve => { resolveOld = resolve }))
      .mockResolvedValueOnce(response({ items: [], total: 0, sent_today: items, sent_today_total: 1 }))
    vi.stubGlobal('fetch', fetchMock)
    const view = render(<RecontactPanel taskRunning={false} refreshKey="initial" onStarted={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: '查找未回复岗位' }))
    await screen.findByRole('checkbox')
    fireEvent.click(screen.getByRole('button', { name: '查找未回复岗位' }))
    view.rerender(<RecontactPanel taskRunning={false} refreshKey="sent" onStarted={vi.fn()} />)
    await screen.findByRole('region', { name: '当日已投递' })
    await act(async () => { resolveOld(response({ items, total: 1 })) })
    expect(screen.queryByRole('checkbox')).toBeNull()
    expect(screen.getByRole('region', { name: '当日已投递' })).toBeTruthy()
  })
})
