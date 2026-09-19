import { useEffect, useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'

type ScoreScope = 'pending' | 'failed' | 'selected' | 'all_scored'

interface ScorePreview {
  eligible_jobs: number
  skipped_jobs: number
  first_attempt_requests: number
  max_attempts_per_job: number
  max_possible_requests: number
  note: string
}

interface ScoreJobsDialogProps {
  open: boolean
  selectedJobIds: string[]
  onClose: () => void
  /** 返回启动结果：成功返回 ok:true（弹窗自动关闭），失败返回错误信息（弹窗保留并展示）。 */
  onStart: (options: { scope: ScoreScope; limit: number | null; job_ids: string[]; force_rescore: boolean }) => Promise<{ ok: boolean; error?: string }>
}

interface ScoringRun {
  id: string
  status: string
  remaining_job_ids: string[]
  progress?: Record<string, number>
  pause_reason?: string
  recoverable?: boolean
}

const scopeLabels: Record<ScoreScope, string> = {
  pending: '未评分 / 失败',
  failed: '只重试失败',
  selected: '岗位池已选',
  all_scored: '重新评分全部有效评分岗位',
}

export function ScoreJobsDialog({ open, selectedJobIds, onClose, onStart }: ScoreJobsDialogProps) {
  const [scope, setScope] = useState<ScoreScope>('pending')
  const [limitText, setLimitText] = useState('全部')
  const [preview, setPreview] = useState<ScorePreview | null>(null)
  const [runs, setRuns] = useState<ScoringRun[]>([])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  const normalizedLimit = limitText.trim()
  const limitValid = normalizedLimit === ''
    || normalizedLimit === '全部'
    || normalizedLimit.toLowerCase() === 'all'
    || (/^\d+$/.test(normalizedLimit) && Number(normalizedLimit) >= 1 && Number(normalizedLimit) <= 10000)
  const limit = useMemo(() => {
    if (normalizedLimit === '' || normalizedLimit === '全部' || normalizedLimit.toLowerCase() === 'all') return null
    return Number(normalizedLimit)
  }, [limitText])

  const loadPreview = async () => {
    if (!limitValid) {
      setPreview(null)
      setMessage('评分数量请输入 1 到 10000 的整数，或输入“全部”。')
      return
    }
    setLoading(true)
    setMessage('')
    try {
      const forceRescore = scope === 'all_scored'
      const jobIds = scope === 'selected' ? selectedJobIds : []
      const res = await fetch('/api/scoring/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ options: { scope, limit, job_ids: jobIds, force_rescore: forceRescore } }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.error || '无法生成评分预览')
      setPreview(data)
    } catch (err) {
      setPreview(null)
      setMessage(err instanceof Error ? err.message : '无法生成评分预览')
    } finally {
      setLoading(false)
    }
  }

  const loadRuns = async () => {
    const res = await fetch('/api/scoring/runs', { cache: 'no-store' })
    if (res.ok) setRuns(await res.json())
  }

  useEffect(() => {
    if (open) {
      void loadPreview()
      void loadRuns()
    }
  }, [open, scope, limit, selectedJobIds.join(',')])

  if (!open) return null

  const start = async () => {
    if (!preview?.eligible_jobs) return
    if (scope === 'all_scored' && !window.confirm('将重新评分所有仍可重评的有效评分岗位，已进入投递链路的岗位不会触碰。确认继续？')) return
    if (!window.confirm(`本轮最多发出 ${preview.max_possible_requests} 次 AI 请求，是否开始？`)) return
    setLoading(true)
    setMessage('')
    try {
      const result = await onStart({ scope, limit, job_ids: scope === 'selected' ? selectedJobIds : [], force_rescore: scope === 'all_scored' })
      if (result.ok) {
        onClose()
        return
      }
      setMessage(result.error || '启动评分失败，请稍后重试。')
    } catch (err) {
      setMessage(err instanceof Error ? err.message : '启动评分失败，请稍后重试。')
    } finally {
      setLoading(false)
    }
  }

  const runAction = async (run: ScoringRun, action: 'pause' | 'resume' | 'end') => {
    setLoading(true)
    setMessage('')
    try {
      const res = await fetch(`/api/scoring/runs/${run.id}/${action}`, { method: 'POST' })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.error || '评分任务操作失败')
      await loadRuns()
      await loadPreview()
      setMessage(action === 'resume' ? '已从剩余岗位继续评分。' : action === 'pause' ? '已请求暂停，当前完成结果会保留。' : '已结束评分任务。')
    } catch (err) {
      setMessage(err instanceof Error ? err.message : '评分任务操作失败')
    } finally {
      setLoading(false)
    }
  }

  const activeRun = runs.find(run => run.status === 'running' || run.status === 'paused')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-5">
      <div className="w-full max-w-xl rounded-3xl border border-card-border bg-card p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-xs font-black tracking-[0.18em] text-primary">AI SCORING</div>
            <h3 className="mt-1 text-2xl font-black">单独 AI 评分</h3>
            <p className="mt-1 text-sm leading-6 text-muted">复用当前岗位池，不重新采集岗位；进入投递链路的岗位不会重评。</p>
          </div>
          <Button variant="secondary" size="sm" onClick={onClose}>关闭</Button>
        </div>
        <div className="mt-5 space-y-4">
          <label className="block text-xs font-bold text-muted">
            评分范围
            <select value={scope} onChange={event => setScope(event.target.value as ScoreScope)} className="mt-1 w-full rounded-xl border border-card-border bg-surface px-3 py-2 text-sm text-foreground outline-none focus:border-primary">
              {Object.entries(scopeLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}
            </select>
          </label>
          <label className="block text-xs font-bold text-muted">
            数量（输入正整数，或输入“全部”）
            <input value={limitText} onChange={event => setLimitText(event.target.value)} className="mt-1 w-full rounded-xl border border-card-border bg-surface px-3 py-2 text-sm text-foreground outline-none focus:border-primary" />
          </label>
          {scope === 'selected' && <div className="rounded-xl bg-secondary px-3 py-2 text-sm text-primary">岗位池已选择 {selectedJobIds.length} 条</div>}
          {preview && (
            <div className="grid grid-cols-2 gap-2 text-sm">
              <Metric label="符合条件" value={preview.eligible_jobs} />
              <Metric label="将跳过" value={preview.skipped_jobs} />
              <Metric label="首轮最多请求" value={preview.first_attempt_requests} />
              <Metric label="考虑重试最大请求" value={preview.max_possible_requests} />
            </div>
          )}
          <div className="rounded-2xl border border-warning-border bg-warning-soft p-3 text-xs leading-5 text-warning-strong">
            基础预览不会调用 AI。正式评分会产生模型请求；单岗位格式错误会记录并继续，鉴权、额度、模型或连续网络错误会安全暂停。
          </div>
          {runs.filter(run => ['running', 'paused'].includes(run.status)).slice(0, 3).map(run => (
            <div key={run.id} className="rounded-2xl border border-card-border bg-surface p-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2"><span className="font-black">{run.status === 'running' ? '评分中' : '已暂停'} · 剩余 {run.remaining_job_ids.length} 个岗位</span><div className="flex gap-2">{run.status === 'running' && <Button variant="secondary" size="sm" onClick={() => void runAction(run, 'pause')}>暂停</Button>}{run.recoverable && <Button size="sm" onClick={() => void runAction(run, 'resume')}>继续</Button>}<Button variant="ghost" size="sm" onClick={() => void runAction(run, 'end')}>结束</Button></div></div>
              {run.pause_reason && <p className="mt-1 text-xs text-muted">{run.pause_reason}</p>}
            </div>
          ))}
          {message && <div className="rounded-xl bg-secondary px-3 py-2 text-sm text-primary">{message}</div>}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={onClose}>取消</Button>
            <Button onClick={start} disabled={loading || !limitValid || !preview?.eligible_jobs || Boolean(activeRun)}>{loading ? '处理中...' : '确认开始评分'}</Button>
          </div>
        </div>
      </div>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="rounded-xl border border-card-border bg-surface p-3"><div className="text-xs text-muted">{label}</div><div className="mt-1 text-xl font-black text-primary">{value}</div></div>
}
