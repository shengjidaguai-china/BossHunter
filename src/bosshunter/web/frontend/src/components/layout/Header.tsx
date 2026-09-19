import { useLocation } from 'react-router-dom'
import { Activity } from 'lucide-react'
import { ThemeToggle } from './ThemeToggle'

const pageTitles: Record<string, string> = {
  '/': '工作台',
  '/jobs': '岗位池',
  '/monitor': '监测执行',
  '/config': '配置',
}

export function Header() {
  const location = useLocation()
  const title = pageTitles[location.pathname] || 'BossHunter'

  return (
    <header className="h-16 border-b border-card-border bg-surface flex items-center justify-between px-6">
      <h1 className="text-lg font-black text-foreground">{title}</h1>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-xs text-muted">
          <Activity className="w-3 h-3 text-success" />
          <span>本地服务运行中</span>
        </div>
        <ThemeToggle />
      </div>
    </header>
  )
}
