import { useEffect, useState } from 'react'
import { Play, Square } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface SessionSummary {
  id: string
  status: string
  collected_job_ids: string[]
  city_totals: Record<string, number>
  state: {
    phase: string
    round: number
    reason_code?: string
    manual_pending_reason?: string
    started_at: string
    deadline_at: string
    next_wake_at?: string | null
    phase_seconds?: Record<string, number>
    stop_requested?: boolean
  }
}

const phaseLabels: Record<string, string> = {
  collecting: '采集中', waiting_round: '轮间休息', waiting_quota: '等待额度',
  waiting_risk: '风险冷却', waiting_retry: '等待恢复', waiting_user: '等待人工处理', finished: '已结束',
}

const reasonLabels: Record<string, string> = {
  captcha: '需要完成验证码', login_required: '登录已失效', blocked: '平台已拦截访问',
  persistent_risk_lock: '风险锁仍生效', rate_limit: '访问频率受限',
  daily_search_page_limit: '今日搜索页额度已用完', daily_detail_page_limit: '今日详情页额度已用完',
  daily_platform_page_limit: '今日页面访问总额度已用完', consecutive_page_failures: '页面连续加载失败',
  search_exhausted: '本轮搜索范围已完成', no_new_jobs: '列表没有新增岗位',
  search_page_not_advanced: '列表不再增长', repeated_search_page: '列表页面重复',
  low_yield: '城市新增量不足', no_jobs_for_search: '搜索结果为空',
  session_deadline: '已到会话截止时间', user_stopped: '已按要求停止',
  timing_gap: '计时中断，需要人工确认', persistence_error: '保存失败，需要检查',
  collection_error: '采集异常，需要检查', salary_decode_failed: '薪资解析失败',
  service_restarted: '服务重启，等待恢复', restart_retry_exhausted: '重启恢复次数已用完',
  retry_exhausted: '自动恢复次数已用完', clock_unreliable: '系统时间发生变化',
  session_error: '会话运行失败', list_load_unconfirmed: '列表尚未可靠加载',
}

export function CollectionSessionsPanel() {
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)
  const [pending, setPending] = useState('')
  useEffect(() => {
    const abort = new AbortController()
    const refresh = async () => {
      try {
        const response = await fetch('/api/collection/sessions', { signal: abort.signal, cache: 'no-store' })
        if (!response.ok) throw new Error('读取持续采集记录失败')
        const data = await response.json()
        if (!abort.signal.aborted) { setSessions(Array.isArray(data) ? data.slice(0, 5) : []); setError('') }
      } catch (cause) {
        if (!abort.signal.aborted) setError(cause instanceof Error ? cause.message : '读取持续采集记录失败')
      }
    }
    void refresh()
    const timer = window.setInterval(() => void refresh(), 15000)
    return () => { abort.abort(); window.clearInterval(timer) }
  }, [revision])
  const act = async (id: string, action: 'stop' | 'continue') => {
    setPending(id)
    try {
      const response = await fetch(`/api/collection/sessions/${encodeURIComponent(id)}/${action}`, { method: 'POST' })
      const result = await response.json()
      if (!response.ok) throw new Error(result.error || '操作失败')
      setError('')
      setRevision(value => value + 1)
    } catch (cause) { setError(cause instanceof Error ? cause.message : '操作失败') }
    finally { setPending('') }
  }
  if (!sessions.length && !error) return null
  return <section className="mt-5 border-t border-card-border pt-4" aria-label="持续采集记录">
    <h3 className="text-sm font-bold">持续采集记录</h3>
    {error && <p role="status" className="mt-2 text-xs text-danger">{error}</p>}
    <div className="mt-2 divide-y divide-card-border">{sessions.map(session => {
      const state = session.state
      const activeMinutes = Math.round((state.phase_seconds?.collecting || 0) / 60)
      const waitingMinutes = Math.round(Object.entries(state.phase_seconds || {}).reduce((sum, [phase, seconds]) => sum + (phase === 'collecting' ? 0 : seconds), 0) / 60)
      return <div key={session.id} className="break-words py-3 text-xs leading-6">
        <div className="flex flex-wrap justify-between gap-x-4"><span className="font-semibold">{new Date(state.started_at).toLocaleString()} · {phaseLabels[state.phase] || state.phase}</span><span>新增 <strong className="tabular-nums">{session.collected_job_ids.length}</strong> · 第 {state.round} 轮</span></div>
        <p className="text-muted">采集 {activeMinutes} 分钟 · 等待 {waitingMinutes} 分钟 · 截止 {new Date(state.deadline_at).toLocaleString()}</p>
        <div className="flex flex-wrap gap-x-4 text-muted">{Object.entries(session.city_totals || {}).map(([city, count]) => <span key={city}>{city} {count}</span>)}</div>
        {(state.manual_pending_reason || state.reason_code) && <p className={state.manual_pending_reason ? 'text-warning' : 'text-muted'}>{state.manual_pending_reason ? '待处理：' : '原因：'}{reasonLabels[state.manual_pending_reason || state.reason_code || ''] || state.manual_pending_reason || state.reason_code}</p>}
        {state.next_wake_at && <p className="text-muted">最早恢复 {new Date(state.next_wake_at).toLocaleString()}</p>}
        {session.status === 'running' && <div className="mt-1 flex gap-2">
          {state.phase === 'waiting_user' && <Button size="sm" variant="secondary" disabled={Boolean(pending) || state.stop_requested} onClick={() => void act(session.id, 'continue')}><Play className="h-3.5 w-3.5" />继续采集</Button>}
          <Button size="sm" variant="secondary" disabled={Boolean(pending) || state.stop_requested} onClick={() => void act(session.id, 'stop')}><Square className="h-3.5 w-3.5" />{state.stop_requested ? '停止中' : '停止全部'}</Button>
        </div>}
      </div>
    })}</div>
  </section>
}
