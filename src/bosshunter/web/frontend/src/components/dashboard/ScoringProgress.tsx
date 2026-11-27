import type { WorkbenchTask } from '@/hooks/useDashboard'

interface ScoringProgressProps {
  metrics?: Record<string, number | string>
  status: string
}

function count(value: number | string | undefined): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? Math.max(0, Math.floor(parsed)) : 0
}

/** Counts processed jobs, including filtered and failed jobs, rather than API requests. */
export function ScoringProgress({ metrics, status }: ScoringProgressProps) {
  const total = count(metrics?.ai_total)
  const completed = total > 0 ? Math.min(count(metrics?.ai_completed), total) : 0
  const percent = total > 0 ? Math.floor(completed * 100 / total) : undefined
  const state = status === 'paused' ? '已暂停'
    : status === 'stopping' ? '正在暂停'
    : status === 'stopped' ? '已停止'
    : status === 'failed' ? '任务失败'
    : status === 'completed_with_errors' ? '已结束，部分失败'
    : total > 0 && completed === total ? '本轮处理完毕'
    : status === 'completed' ? '已结束'
    : '评分中'

  const emptyText = ['running', 'stopping'].includes(status) ? '正在准备待评分岗位…' : '暂无评分计数'

  return (
    <section className="mt-3 rounded-xl border border-card-border bg-surface px-3 py-3" aria-label="本轮 AI 评分进度">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <span className="font-semibold">本轮 AI 评分 · {state}</span>
        <span className="tabular-nums text-muted">{total > 0 ? `已处理 ${completed} / ${total} · ${percent}%` : emptyText}</span>
      </div>
      <div
        role="progressbar"
        aria-label="AI 评分进度"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        aria-valuetext={total > 0 ? `${state}，已处理 ${completed} / ${total} 个岗位，${percent}%` : `${state}，${emptyText}`}
        className="mt-2 h-2 overflow-hidden rounded-full bg-secondary"
      >
        <div className={`h-full rounded-full transition-[width] duration-500 motion-reduce:transition-none ${status === 'failed' ? 'bg-danger' : 'bg-primary'} ${percent === undefined && status === 'running' ? 'animate-pulse motion-reduce:animate-none' : ''}`} style={{ width: `${percent ?? (status === 'running' ? 15 : 0)}%` }} />
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
        <span>通过 {count(metrics?.ai_passed)}</span>
        <span>过滤 {count(metrics?.ai_filtered)}</span>
        <span className={count(metrics?.ai_failed) > 0 ? 'text-danger' : undefined}>失败 {count(metrics?.ai_failed)}</span>
        <span>按岗位计数，重试不重复计入；恢复任务后显示本轮剩余岗位的进度。</span>
      </div>
    </section>
  )
}

export function TaskScoringProgress({ task }: { task: WorkbenchTask | null }) {
  if (!task || (task.mode !== 'score' && task.mode !== 'rescore'
    && task.metrics?.ai_total === undefined && task.progress?.outcome !== 'scoring')) return null
  return <ScoringProgress metrics={task.metrics} status={task.status} />
}
