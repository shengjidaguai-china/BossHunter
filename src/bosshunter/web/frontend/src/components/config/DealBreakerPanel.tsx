import { Filter, ShieldOff } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { TagsInput } from '@/components/ui/tags-input'

type DealBreakerPanelProps = {
  dealBreakers: string[]
  jdBreakers: string[]
  onChangeTitle: (next: string[]) => void
  onChangeJd: (next: string[]) => void
  dirty: boolean
}

/**
 * 绝对不投：职位名/JD 命中这些词就整条跳过，不进 AI 评分。
 * 与「搜索关键词」互为补充——关键词决定找什么，否决词决定坚决不碰什么。
 */
export function DealBreakerPanel({
  dealBreakers,
  jdBreakers,
  onChangeTitle,
  onChangeJd,
  dirty,
}: DealBreakerPanelProps) {
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState('')
  const [error, setError] = useState('')

  const applyToExisting = async () => {
    setBusy(true)
    setError('')
    setNote('')
    try {
      const res = await fetch('/api/jobs/apply-deal-breakers', { method: 'POST' })
      const data = await res.json().catch(() => ({}))
      if (!res.ok || data.error) {
        setError(data.error || '重筛失败')
        return
      }
      const samples = (data.samples || [])
        .slice(0, 3)
        .map((item: { title: string; keyword: string }) => `${item.title}（${item.keyword}）`)
        .join('、')
      setNote(
        `已检查 ${data.checked ?? 0} 条岗位，跳过 ${data.filtered ?? 0} 条` +
          (samples ? `：${samples}${data.filtered > 3 ? ' 等' : ''}` : ''),
      )
    } catch {
      setError('网络错误，重筛失败')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-xs text-muted">
        搜索关键词决定「去找什么」，这里的否决词决定「无论如何都不投什么」：命中即跳过，不进入 AI 评分。
      </p>

      <div>
        <label className="mb-1 block text-xs text-foreground">职位名含这些词 → 直接跳过</label>
        <TagsInput
          value={dealBreakers}
          onChange={onChangeTitle}
          placeholder="如：算法、研发、Infra、外包"
        />
        <p className="mt-1 text-xs text-muted">
          例如填「算法」「研发」「Infra」，则「算法工程师」「AI 研发实习生」「AI Infra 实习生」全部跳过；不区分大小写，「AI-Infra」也会命中「Infra」。
        </p>
      </div>

      <div>
        <label className="mb-1 block text-xs text-foreground">JD 含这些词 → 直接跳过（可选，慎用）</label>
        <TagsInput
          value={jdBreakers}
          onChange={onChangeJd}
          placeholder="如：纯销售、需要驻场、频繁出差"
        />
        <p className="mt-1 text-xs text-muted">
          JD 里出现这些词才会跳过。因为 JD 常提到「与研发团队协作」这类无关表述，建议只填确实不能接受的硬条件。
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={applyToExisting}
          disabled={busy || dirty || (!dealBreakers.length && !jdBreakers.length)}
        >
          <Filter className="mr-1 h-3 w-3" />
          {busy ? '重筛中…' : '按当前否决词重筛已有岗位'}
        </Button>
        <span className="text-xs text-muted">
          {dirty ? '请先保存配置再重筛' : '只影响未投递岗位，已发送的不会被改动'}
        </span>
      </div>

      {note ? <p className="text-xs text-success">{note}</p> : null}
      {error ? (
        <p className="flex items-center gap-1 text-xs text-danger">
          <ShieldOff className="h-3 w-3" />
          {error}
        </p>
      ) : null}
    </div>
  )
}
