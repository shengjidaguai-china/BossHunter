import { useCallback, useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import type { Job, WorkbenchTask } from '@/hooks/useDashboard'

interface RecontactJob extends Job {
  last_contact_at: string
  recontact_count: number
  sent_today_at?: string | null
}

export function RecontactPanel({
  taskRunning,
  onStarted,
  refreshKey = '',
  defaultGreeting = '',
}: {
  taskRunning: boolean
  onStarted: (task: WorkbenchTask) => void | Promise<void>
  refreshKey?: string
  defaultGreeting?: string
}) {
  const [hours, setHours] = useState('48')
  const [jobs, setJobs] = useState<RecontactJob[]>([])
  const [total, setTotal] = useState(0)
  const [sentToday, setSentToday] = useState<RecontactJob[]>([])
  const [sentTodayTotal, setSentTodayTotal] = useState(0)
  const [selected, setSelected] = useState<string[]>([])
  const [greeting, setGreeting] = useState(defaultGreeting.trim())
  const [configuredGreeting, setConfiguredGreeting] = useState(defaultGreeting.trim())
  const [editingGreeting, setEditingGreeting] = useState(false)
  const greetingEdited = useRef(false)
  const [loading, setLoading] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [saving, setSaving] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const minHours = Number(hours)
  const validHours = Number.isInteger(minHours) && minHours >= 1 && minHours <= 720
  const validGreeting = greeting.trim().length > 0 && greeting.trim().length <= 300
  const requestVersion = useRef(0)
  const previousRefreshKey = useRef(refreshKey)

  useEffect(() => {
    setConfiguredGreeting(defaultGreeting.trim())
    if (!greetingEdited.current) setGreeting(defaultGreeting.trim())
  }, [defaultGreeting])

  const loadCandidates = useCallback(async () => {
    if (!validHours) return
    const version = ++requestVersion.current
    setLoading(true)
    setError('')
    setNotice('')
    setConfirming(false)
    try {
      const response = await fetch(`/api/workbench/recontact?min_hours=${minHours}`, { cache: 'no-store' })
      const data = await response.json().catch(() => ({}))
      if (version !== requestVersion.current) return
      if (!response.ok) throw new Error(data.error || '读取未回复岗位失败，请检查后台服务是否已更新')
      if (!Array.isArray(data.items)) throw new Error('未回复岗位列表格式不正确')
      setJobs(data.items)
      setTotal(Number(data.total || 0))
      setSentToday(Array.isArray(data.sent_today) ? data.sent_today : [])
      setSentTodayTotal(Number(data.sent_today_total || 0))
      const configured = typeof data.default_greeting === 'string' ? data.default_greeting.trim() : ''
      setConfiguredGreeting(configured)
      if (!greetingEdited.current) setGreeting(configured)
      setSelected([])
      setLoaded(true)
    } catch (cause) {
      if (version === requestVersion.current) setError(cause instanceof Error ? cause.message : '读取未回复岗位失败')
    } finally {
      if (version === requestVersion.current) setLoading(false)
    }
  }, [minHours, validHours])

  useEffect(() => {
    const changed = previousRefreshKey.current !== refreshKey
    previousRefreshKey.current = refreshKey
    if (changed && (loaded || requestVersion.current > 0)) void loadCandidates()
  }, [refreshKey, loaded, loadCandidates])

  useEffect(() => () => { requestVersion.current++ }, [])

  const startRecontact = async () => {
    if (!selected.length || !validHours || !validGreeting || saving || taskRunning) return
    setSaving(true)
    setError('')
    try {
      const response = await fetch('/api/workbench/recontact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_ids: selected, min_hours: minHours, greeting: greeting.trim(), confirmed: true }),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        if (response.status === 404 || response.status === 405) throw new Error('后台尚未加载再次投递功能，请重新启动 BossHunter 后重试')
        throw new Error(data.error || '启动再次投递失败')
      }
      if (!data.id || data.mode !== 'recontact') throw new Error('后台没有确认任务已启动，请刷新检查')
      setConfirming(false)
      setNotice(`已提交 ${selected.length} 个岗位，后台会逐一核对 HR 回复后再联系。`)
      setSelected([])
      await onStarted(data as WorkbenchTask)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '启动再次投递失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section aria-label="未回复再次投递" className="rounded-2xl border border-card-border bg-card p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-black">未回复再次投递</h3>
          <p className="mt-1 text-xs leading-5 text-muted">筛选已投递且没有 HR 回复记录的 BOSS 岗位。发送前会再次核对聊天，已回复岗位自动跳过。</p>
        </div>
        <Button variant="secondary" size="sm" disabled={!validHours || loading || saving} onClick={() => void loadCandidates()}>
          {loading ? '查找中...' : '查找未回复岗位'}
        </Button>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <label className="text-sm" htmlFor="recontact-hours">最短再次联系间隔（小时）</label>
        <input id="recontact-hours" type="number" min={1} max={720} step={1} value={hours} disabled={saving || loading}
          onChange={event => {
            requestVersion.current++
            setLoading(false)
            setHours(event.target.value)
            setLoaded(false)
            setJobs([])
            setSelected([])
            setConfirming(false)
          }}
          className="w-24 rounded-xl border border-card-border bg-surface px-3 py-2 text-sm outline-none focus:border-primary" />
        <span className="text-xs text-muted">按最后一次实际发送计算，默认 48 小时；北京时间当日已投递的岗位不再重复发送。</span>
      </div>
      {!validHours && <p className="mt-2 text-xs text-danger">请输入 1 至 720 的整数小时。</p>}
      <section aria-label="本次招呼语编辑" className="mt-4 rounded-xl border border-card-border bg-surface p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <label htmlFor="recontact-greeting" className="text-sm font-semibold">本次招呼语</label>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" disabled={saving} onClick={() => { setEditingGreeting(true); setConfirming(false) }}>修改招呼语</Button>
            <Button variant="ghost" size="sm" disabled={saving || !configuredGreeting} onClick={() => {
              greetingEdited.current = false
              setGreeting(configuredGreeting)
              setEditingGreeting(false)
              setConfirming(false)
            }}>使用配置招呼语</Button>
          </div>
        </div>
        <p className="mt-1 text-xs text-muted">默认使用配置里的打招呼语；修改只对本次投递生效，不改动全局配置。</p>
        <textarea id="recontact-greeting" value={greeting} maxLength={300} rows={4} disabled={saving} readOnly={!editingGreeting}
          onChange={event => { greetingEdited.current = true; setGreeting(event.target.value); setConfirming(false) }}
          placeholder="请在配置中填写打招呼语，或点击“修改招呼语”输入本次文案。"
          className="mt-2 w-full rounded-xl border border-card-border bg-surface p-3 text-sm leading-6 outline-none focus:border-primary" />
        {!validGreeting && <p role="alert" className="mt-2 text-xs text-danger">请填写 1 至 300 字的本次招呼语，不会自动使用历史文案。</p>}
        <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
          <span className="text-xs text-muted">{greeting.length}/300 · 与首次投递共用每日发送额度、间隔和时间窗口。</span>
          <Button size="sm" disabled={!selected.length || !validGreeting || taskRunning || saving || loading} onClick={() => { setConfirming(true); setError('') }}>
            再次投递已选 {selected.length} 个
          </Button>
        </div>
        {taskRunning && <p className="mt-2 text-xs text-muted">当前有后台任务在运行，结束后可开始再次投递。</p>}
      </section>
      {error && <p role="alert" className="mt-3 rounded-xl bg-danger-soft p-3 text-sm text-danger">{error}</p>}
      {notice && <p role="status" className="mt-3 text-sm text-primary">{notice}</p>}
      {loaded && (
        <div className="mt-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm">符合间隔且无回复记录：{total} 个，已选 {selected.length} 个</p>
            <Button variant="secondary" size="sm" disabled={!jobs.length || saving || loading} onClick={() => {
              setSelected(selected.length === jobs.length ? [] : jobs.map(job => job.id))
              setConfirming(false)
            }}>{jobs.length > 0 && selected.length === jobs.length ? '清空选择' : '全选候选岗位'}</Button>
          </div>
          {jobs.length ? (
            <div className="mt-3 max-h-80 divide-y divide-card-border overflow-y-auto rounded-xl border border-card-border">
              {jobs.map(job => (
                <label key={job.id} className="flex cursor-pointer items-start gap-3 p-3 hover:bg-surface">
                  <input type="checkbox" aria-label={`选择再次投递：${job.company}｜${job.title}`} checked={selected.includes(job.id)} disabled={saving || loading}
                    onChange={() => {
                      setSelected(previous => previous.includes(job.id) ? previous.filter(id => id !== job.id) : [...previous, job.id])
                      setConfirming(false)
                    }} className="mt-1 accent-primary" />
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-semibold">{job.company}｜{job.title}</span>
                    <span className="mt-1 block text-xs text-muted">上次联系：{new Date(`${job.last_contact_at.replace(' ', 'T')}Z`).toLocaleString('zh-CN')} · 已再次联系 {job.recontact_count} 次</span>
                    <span className="mt-1 block line-clamp-2 text-xs leading-5 text-muted">{greeting.trim() || '请设置本次招呼语，不会使用历史文案。'}</span>
                  </span>
                </label>
              ))}
            </div>
          ) : <p className="mt-3 text-sm text-muted">暂无符合条件的未回复岗位。可以调整间隔后重新查找。</p>}
          {total > jobs.length && <p className="mt-2 text-xs text-muted">本轮显示最早联系的 {jobs.length} 个岗位。</p>}
          {sentTodayTotal > 0 && (
            <section aria-label="当日已投递" className="mt-4 rounded-xl border border-card-border bg-surface p-3">
              <h4 className="text-sm font-bold">当日已投递 {sentTodayTotal} 个</h4>
              <p className="mt-1 text-xs text-muted">已移出可选候选，当天不能再次勾选或发送（北京时间）；次日仍需满足设置的联系间隔。</p>
              <div className="mt-2 max-h-48 divide-y divide-card-border overflow-y-auto">
                {sentToday.map(job => (
                  <div key={job.id} className="py-2 text-sm">
                    <span>{job.company}｜{job.title}</span>
                    <span className="ml-2 rounded-full bg-primary/10 px-2 py-1 text-xs text-primary">当日已投递</span>
                    {job.sent_today_at && <span className="mt-1 block text-xs text-muted">投递时间：{new Date(`${job.sent_today_at.replace(' ', 'T')}Z`).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })}</span>}
                  </div>
                ))}
              </div>
              {sentTodayTotal > sentToday.length && <p className="mt-2 text-xs text-muted">显示其中 {sentToday.length} 个岗位。</p>}
            </section>
          )}
        </div>
      )}
      {confirming && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4" role="alertdialog" aria-modal="true" aria-label="确认再次投递">
          <div className="w-full max-w-xl rounded-2xl border border-card-border bg-card p-5 shadow-2xl">
            <h4 className="text-lg font-black">确认再次联系 {selected.length} 个岗位？</h4>
            <p className="mt-3 text-sm leading-6 text-muted">仅处理所选岗位，发送前会核验聊天记录。HR 已回复、记录无法确认或间隔未到的岗位会跳过。</p>
            <p className="mt-3 whitespace-pre-wrap rounded-xl bg-surface p-3 text-sm leading-6">{greeting.trim()}</p>
            {error && <p role="alert" className="mt-3 text-sm text-danger">{error}</p>}
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="secondary" size="sm" disabled={saving} onClick={() => setConfirming(false)}>取消</Button>
              <Button size="sm" disabled={saving || taskRunning || !validGreeting} onClick={() => void startRecontact()}>{saving ? '提交中...' : `确认再次投递 ${selected.length} 个`}</Button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
