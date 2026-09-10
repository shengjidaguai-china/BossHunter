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
      <div className="grid grid-cols-3 gap-x-3 gap-y-5 lg:grid-cols-6">
        {steps.map((step, i) => (
          <div key={step.label} className="relative min-w-0">
            <div className="flex flex-col items-center">
              <div className="w-12 h-12 rounded-xl bg-white border border-card-border flex items-center justify-center mb-2 hover:border-primary/50 hover:shadow-md transition-all shadow-sm">
                <step.icon className="w-5 h-5 text-primary" />
              </div>
              <span className="text-xs font-black text-foreground">{step.label}</span>
              <span className="text-[10px] text-muted mt-0.5">{step.desc}</span>
            </div>
            {i < steps.length - 1 && (
              <div className="absolute left-[calc(50%+28px)] right-[calc(-50%+16px)] top-6 hidden h-px bg-card-border lg:block" />
            )}
          </div>
        ))}
      </div>
      <p className="text-xs text-muted mt-4">
        可从上方选择运行全流程、单独采集或单独监测；投递前需要人工确认。
      </p>
    </div>
  )
}
