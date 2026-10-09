import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import type { FunnelData } from '@/hooks/useDashboard'

interface FunnelCardsProps {
  data: FunnelData
}

const funnelSteps = [
  { key: '采集总数', color: 'text-info', bg: 'bg-info-soft' },
  { key: '初筛通过', color: 'text-cyan', bg: 'bg-cyan-soft' },
  { key: 'AI评分', color: 'text-success', bg: 'bg-success-soft' },
  { key: '人工确认', color: 'text-warning', bg: 'bg-warning-soft' },
]

export function FunnelCards({ data }: FunnelCardsProps) {
  const total = data['采集总数'] || 0

  return (
    <div className="grid grid-cols-4 gap-3">
      {funnelSteps.map((step, i) => {
        const count = data[step.key] || 0
        const prevCount = i === 0 ? count : (data[funnelSteps[i - 1].key] || 0)
        const rate = prevCount > 0 && i > 0 ? ((count / prevCount) * 100).toFixed(1) + '%' : ''

        return (
          <Card key={step.key}>
            <CardHeader className="pb-2 p-4">
              <CardTitle className="text-xs text-muted font-bold">{step.key}</CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className={`text-2xl font-black ${step.color}`}>{count}</div>
              {rate && <p className="text-xs text-muted mt-1">转化率 {rate}</p>}
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
