import { Search, Bot, MessageSquare, CheckCircle, Send, Eye } from 'lucide-react'

const steps = [
  { icon: Search, label: '采集', desc: '搜索岗位' },
  { icon: Bot, label: 'AI评分', desc: '匹配打分' },
  { icon: MessageSquare, label: '招呼语', desc: '个性生成' },
  { icon: CheckCircle, label: '人工确认', desc: '审核通过' },
  { icon: Send, label: '发送', desc: '自动投递' },
  { icon: Eye, label: '监控', desc: '跟进回复' },
]

export function PipelineFlow() {
  return (
    <div className="rounded-2xl border border-card-border bg-[#FFFCFA] p-6">
      <h3 className="text-sm font-black text-foreground mb-4">BossHunter 自动求职流程</h3>
      <div className="flex items-center justify-between">
        {steps.map((step, i) => (
          <div key={step.label} className="flex items-center">
            <div className="flex flex-col items-center">
              <div className="w-12 h-12 rounded-xl bg-white border border-card-border flex items-center justify-center mb-2 hover:border-primary/50 hover:shadow-md transition-all shadow-sm">
                <step.icon className="w-5 h-5 text-primary" />
              </div>
              <span className="text-xs font-black text-foreground">{step.label}</span>
              <span className="text-[10px] text-muted mt-0.5">{step.desc}</span>
            </div>
            {i < steps.length - 1 && (
              <div className="w-8 h-px bg-gradient-to-r from-[#F2E7DE] to-[#F2E7DE] mx-2 mb-6" />
            )}
          </div>
        ))}
      </div>
      <p className="text-xs text-muted mt-4">
        每个步骤都可独立运行，也可 <code className="rounded bg-white px-1.5 py-0.5 text-primary font-mono text-[11px] border border-card-border">bosshunter run</code> 一键全流程执行
      </p>
    </div>
  )
}
