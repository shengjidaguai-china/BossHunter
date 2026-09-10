import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import type { TopCompany } from '@/hooks/useDashboard'

interface TopCompaniesProps {
  data: TopCompany[]
}

export function TopCompanies({ data }: TopCompaniesProps) {
  if (!data.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="font-black text-foreground">高分公司 TOP5</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted">暂无数据，完成岗位采集和 AI 评分后显示</p>
        </CardContent>
      </Card>
    )
  }

  const maxScore = Math.max(...data.map(d => d.avg_score))

  return (
    <Card>
      <CardHeader>
        <CardTitle className="font-black text-foreground">高分公司 TOP5</CardTitle>
      </CardHeader>
      <CardContent className="p-4 pt-0">
        <div className="space-y-3">
          {data.map((company, i) => (
            <div key={i} className="flex items-center gap-3">
              <span className="text-xs font-black text-primary w-4">{i + 1}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-bold text-foreground truncate max-w-[140px]">{company.company}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted">{company.job_count} 岗</span>
                    <span className="text-xs font-mono font-black text-primary">{company.avg_score}</span>
                  </div>
                </div>
                <div className="h-1.5 bg-[#FFF0E5] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary rounded-full transition-all"
                    style={{ width: `${(company.avg_score / maxScore) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
