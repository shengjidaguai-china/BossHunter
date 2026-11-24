import { AlertTriangle, ChevronDown, ChevronRight, RotateCcw, ShieldCheck } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'

export type FilterSample = {
  id: string
  title: string
  company: string
  city: string
  salary: string
  score: number
  category: string
  filter_reason: string
  reason_category: string
  url: string
  created_at: string
}

type CategoryStat = {
  category: string
  count: number
  share: number
  avg_score: number
  samples: FilterSample[]
}

type FilterStats = {
  total: number
  categories: CategoryStat[]
  reasons: { reason: string; count: number; share: number }[]
  score_bands: { band: string; count: number }[]
  top_companies: { company: string; count: number }[]
}

type Props = {
  onRestored?: () => void
}

/** 过滤分析：被过滤的岗位集中在哪些类型、为什么被过滤，可一键恢复投递。 */
export function FilterInsightsPanel({ onRestored }: Props) {
  const [stats, setStats] = useState<FilterStats | null>(null)
  const [open, setOpen] = useState(false)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const res = await fetch('/api/jobs/filter-stats')
      const data = await res.json().catch(() => ({}))
      if (!res.ok || data.error) {
        setError(data.error || '读取过滤统计失败')
        return
      }
      setStats(data as FilterStats)
      setError('')
    } catch {
      setError('网络错误，无法读取过滤统计')
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const restore = async (payload: { job_ids?: string[]; category?: string; all?: boolean }) => {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const res = await fetch('/api/jobs/unfilter', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok || data.error) {
        setError(data.error || '恢复失败')
        return
      }
      setNotice(`已恢复 ${data.restored ?? 0} 个岗位到「待确认」，可在上方勾选后一键投递`)
      await load()
      onRestored?.()
    } catch {
      setError('网络错误，恢复失败')
    } finally {
      setBusy(false)
    }
  }

  const total = stats?.total ?? 0

  return (
    <section className="mb-4 rounded-2xl border border-card-border bg-surface">
      <button
        type="button"
        className="flex w-full flex-wrap items-center justify-between gap-2 px-4 py-3 text-left"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
      >
        <span className="flex items-center gap-2 text-sm font-black">
          {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          <AlertTriangle className="h-4 w-4 text-warning" />
          过滤分析
          <span className="rounded-full bg-secondary px-2 py-0.5 text-xs font-bold text-muted">
            已过滤 {total} 条
          </span>
        </span>
        <span className="text-xs text-muted">看被过滤的都是什么类型、为什么被过滤，可随时恢复投递</span>
      </button>

      {open ? (
        <div className="space-y-3 border-t border-card-border px-4 py-3">
          {!stats ? (
            <p className="text-xs text-muted">加载中…</p>
          ) : total === 0 ? (
            <p className="text-xs text-muted">当前没有被过滤的岗位。</p>
          ) : (
            <>
              <div className="flex flex-wrap gap-2 text-xs">
                {stats.reasons.map((item) => (
                  <span key={item.reason} className="rounded-full border border-card-border bg-card px-2 py-1">
                    {item.reason} <b>{item.count}</b>
                    <span className="ml-1 text-muted">{item.share}%</span>
                  </span>
                ))}
                {stats.score_bands.map((band) => (
                  <span key={band.band} className="rounded-full border border-card-border bg-card px-2 py-1 text-muted">
                    {band.band} <b className="text-foreground">{band.count}</b>
                  </span>
                ))}
              </div>

              <div className="space-y-2">
                {stats.categories.map((item) => {
                  const isOpen = expanded === item.category
                  return (
                    <div key={item.category} className="rounded-xl border border-card-border bg-card">
                      <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
                        <button
                          type="button"
                          className="flex min-w-0 flex-1 items-center gap-2 text-left text-xs"
                          onClick={() => setExpanded(isOpen ? null : item.category)}
                        >
                          {isOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                          <span className="font-bold">{item.category}</span>
                          <span className="rounded bg-secondary px-1.5 py-0.5 font-bold">{item.count}</span>
                          <span className="text-muted">{item.share}%</span>
                          <span className="text-muted">平均分 {item.avg_score}</span>
                        </button>
                        <div className="flex items-center gap-1">
                          <div className="hidden h-1.5 w-24 overflow-hidden rounded bg-secondary sm:block">
                            <div className="h-full bg-warning" style={{ width: `${Math.min(item.share, 100)}%` }} />
                          </div>
                          <Button
                            variant="secondary"
                            size="sm"
                            disabled={busy}
                            onClick={() => void restore({ category: item.category })}
                          >
                            <RotateCcw className="mr-1 h-3 w-3" />恢复该分类
                          </Button>
                        </div>
                      </div>
                      {isOpen ? (
                        <ul className="space-y-1 border-t border-card-border px-3 py-2">
                          {item.samples.map((job) => (
                            <li key={job.id} className="flex flex-wrap items-start justify-between gap-2 text-[11px]">
                              <div className="min-w-0">
                                <p className="font-bold">
                                  {job.title || '（无标题）'}
                                  <span className="ml-2 font-normal text-muted">{job.company}</span>
                                  <span className="ml-2 font-normal text-muted">{job.city} {job.salary}</span>
                                </p>
                                <p className="text-muted">
                                  分数 {job.score} · {job.filter_reason || job.reason_category}
                                </p>
                              </div>
                              <Button
                                variant="ghost"
                                size="sm"
                                disabled={busy}
                                onClick={() => void restore({ job_ids: [job.id] })}
                              >
                                <RotateCcw className="mr-1 h-3 w-3" />取消过滤
                              </Button>
                            </li>
                          ))}
                          {item.count > item.samples.length ? (
                            <li className="text-[11px] text-muted">
                              仅展示分数最高的 {item.samples.length} 条；点「恢复该分类」可一次放回全部 {item.count} 条。
                            </li>
                          ) : null}
                        </ul>
                      ) : null}
                    </div>
                  )
                })}
              </div>

              {stats.top_companies.length ? (
                <p className="text-[11px] text-muted">
                  被过滤最多的公司：
                  {stats.top_companies
                    .slice(0, 5)
                    .map((item) => `${item.company}(${item.count})`)
                    .join('、')}
                </p>
              ) : null}

              <div className="flex flex-wrap items-center gap-2">
                <Button variant="secondary" size="sm" onClick={() => void load()} disabled={busy}>
                  <ShieldCheck className="mr-1 h-3 w-3" />刷新统计
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={busy || total === 0}
                  onClick={() => {
                    if (window.confirm(`把全部 ${total} 个已过滤岗位恢复为「待确认」？恢复后可勾选并一键投递。`)) {
                      void restore({ all: true })
                    }
                  }}
                >
                  <RotateCcw className="mr-1 h-3 w-3" />全部取消过滤
                </Button>
              </div>
            </>
          )}
          {notice ? <p className="text-xs text-success">{notice}</p> : null}
          {error ? <p className="text-xs text-danger">{error}</p> : null}
        </div>
      ) : null}
    </section>
  )
}
