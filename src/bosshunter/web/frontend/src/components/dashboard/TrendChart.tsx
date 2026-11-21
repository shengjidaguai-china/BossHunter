import { useMemo } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import type { ActivityData } from '@/hooks/useDashboard'

interface TrendChartProps {
  data: ActivityData[]
}

export function TrendChart({ data }: TrendChartProps) {
  const chartData = useMemo(() => {
    const dayMap = new Map<string, { day: string; send: number; reply: number }>()
    const today = new Date()

    // Activity is grouped by UTC day in the database.
    for (let i = 6; i >= 0; i--) {
      const d = new Date(today)
      d.setUTCDate(d.getUTCDate() - i)
      const key = d.toISOString().split('T')[0]
      dayMap.set(key, { day: key.slice(5), send: 0, reply: 0 })
    }

    // Fill in actual data
    data.forEach(item => {
      const point = dayMap.get(item.day)
      if (!point) return
      if (item.action === 'sent') point.send += item.cnt
      else if (item.action === 'replied' || item.action === 'auto_replied') point.reply += item.cnt
    })

    return Array.from(dayMap.values())
  }, [data])

  return (
    <Card>
      <CardHeader>
        <CardTitle className="font-black text-foreground">7 日趋势</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="day" stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <Tooltip
                contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '12px', boxShadow: '0 4px 12px hsl(var(--primary) / 0.08)' }}
                labelStyle={{ color: 'hsl(var(--foreground))', fontWeight: 700 }}
                itemStyle={{ color: 'hsl(var(--muted-foreground))', fontSize: '12px' }}
              />
              <Legend wrapperStyle={{ fontSize: '12px', color: 'hsl(var(--muted-foreground))' }} />
              <Line type="monotone" dataKey="send" name="发送" stroke="hsl(var(--success))" strokeWidth={2} dot={{ r: 3, fill: 'hsl(var(--success))' }} activeDot={{ r: 5 }} />
              <Line type="monotone" dataKey="reply" name="回复" stroke="hsl(var(--primary))" strokeWidth={2} dot={{ r: 3, fill: 'hsl(var(--primary))' }} activeDot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
