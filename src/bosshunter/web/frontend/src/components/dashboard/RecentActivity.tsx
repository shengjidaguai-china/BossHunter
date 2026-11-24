import { useId, useState } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge, type BadgeProps } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { CollapsibleToggleButton } from '@/components/dashboard/CollapsibleControls'
import type { HistoryItem } from '@/hooks/useDashboard'

interface RecentActivityProps {
  data: HistoryItem[]
  onMarkAllRead?: () => Promise<void> | void
  markingRead?: boolean
}

const ACTION_LABELS: Record<string, string> = {
  scrape: '采集',
  scored: '评分',
  sent: '发送',
  manual_sent: '手动已发送',
  replied: '回复',
  hr_reply_detected: 'HR 消息',
  auto_replied: '自动回复',
  error: '错误',
  approved: '确认',
  filtered: '过滤',
  unfiltered: '恢复待投',
  greeting_selected: '确认招呼语',
  greeting_edited: '编辑招呼语',
  greeting_failed: '生成失败',
  needs_resume: '索要简历',
  resume_sent: '简历',
  resume_failed: '简历失败',
}

const ACTION_VARIANTS: Record<string, BadgeProps['variant']> = {
  scored: 'scored',
  sent: 'sent',
  manual_sent: 'sent',
  replied: 'replied',
  hr_reply_detected: 'reply_pending',
  auto_replied: 'auto_replied',
  error: 'error',
  greeting_failed: 'error',
  resume_failed: 'error',
  approved: 'approved',
  greeting_selected: 'approved',
  filtered: 'filtered',
  unfiltered: 'ready',
  needs_resume: 'needs_resume',
  resume_sent: 'resume_sent',
}

export function RecentActivity({ data, onMarkAllRead, markingRead = false }: RecentActivityProps) {
  const [collapsed, setCollapsed] = useState(false)
  const overflowId = useId()
  const items = Array.isArray(data) ? data : []
  const canCollapse = items.length > 1
  const isCollapsed = canCollapse && collapsed

  const formatTime = (dateStr: string) => {
    if (!dateStr) return ''
    const d = new Date(dateStr)
    if (Number.isNaN(d.getTime())) return ''
    return `${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
  }

  const renderActivityRow = (item: HistoryItem) => (
    <div key={item.id} className="flex items-start gap-2">
      <div className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-3 gap-y-0.5">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <Badge variant={ACTION_VARIANTS[item.action] || 'default'} className="px-1.5 py-0 text-[10px]">
            {ACTION_LABELS[item.action] || item.action}
          </Badge>
          <span className="truncate text-xs font-bold text-foreground">
            {item.company} · {item.title}
          </span>
        </div>
        <time className="shrink-0 text-[11px] text-muted" dateTime={item.created_at}>{formatTime(item.created_at)}</time>
      </div>
    </div>
  )

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 space-y-0 p-4 pb-3">
        <CardTitle className="font-black text-foreground">
          最近活动
          {items.length > 0 && (
            <span className="ml-2 text-xs font-normal text-muted">{items.length} 条未读</span>
          )}
        </CardTitle>
        <div className="flex items-center gap-1.5">
          {items.length > 0 && onMarkAllRead && (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={markingRead}
              onClick={() => void onMarkAllRead()}
            >
              {markingRead ? '标记中...' : '一键已读'}
            </Button>
          )}
          {canCollapse && (
            <CollapsibleToggleButton
              sectionName="最近活动"
              collapsed={isCollapsed}
              controlsId={overflowId}
              onToggle={() => setCollapsed(value => !value)}
            />
          )}
        </div>
      </CardHeader>
      <CardContent className="p-4 pt-0">
        {items.length === 0 ? (
          <p className="text-sm text-muted">暂无未读活动</p>
        ) : (
          <div>
            {renderActivityRow(items[0])}
            {canCollapse && (
              <div id={overflowId} className="collapsible-overflow" hidden={isCollapsed}>
                <div className="mt-2 space-y-2">
                  {items.slice(1).map(renderActivityRow)}
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
