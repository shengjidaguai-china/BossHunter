import { NavLink } from 'react-router-dom'
import { BriefcaseBusiness, Github, LayoutDashboard, Radar, Settings } from 'lucide-react'
import { useEffect, useState } from 'react'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: '工作台' },
  { to: '/jobs', icon: BriefcaseBusiness, label: '岗位池' },
  { to: '/monitor', icon: Radar, label: '监测执行' },
  { to: '/config', icon: Settings, label: '配置' },
]

const GITHUB_URL = 'https://github.com/powerycy/BossHunter'

interface SidebarProps {
  pendingReplies?: number
}

export function Sidebar({ pendingReplies: pendingRepliesProp }: SidebarProps) {
  const [pendingReplies, setPendingReplies] = useState(pendingRepliesProp ?? 0)

  useEffect(() => {
    if (pendingRepliesProp !== undefined) {
      setPendingReplies(pendingRepliesProp)
      return
    }

    const fetchPendingReplies = async () => {
      try {
        const res = await fetch('/api/history/unresolved-replies/count')
        const data = await res.json()
        setPendingReplies(Number(data.count) || 0)
      } catch {
        setPendingReplies(0)
      }
    }

    fetchPendingReplies()
    const interval = setInterval(fetchPendingReplies, 30000)
    return () => clearInterval(interval)
  }, [pendingRepliesProp])

  return (
    <aside className="flex w-16 shrink-0 flex-col border-r border-card-border bg-white md:w-60">
      <div className="flex h-16 shrink-0 items-center justify-center border-b border-card-border md:justify-start md:px-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-primary text-white flex items-center justify-center shadow-lg shadow-primary/20">
            <span className="font-black text-sm">BH</span>
          </div>
          <div className="hidden md:block">
            <div className="font-black text-sm tracking-tight text-foreground">BossHunter</div>
            <div className="text-[11px] text-muted">v2.4.0 · 本地控制台</div>
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-1.5 py-4 md:px-3">
        {navItems.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `relative flex items-center justify-center gap-3 rounded-xl px-1 py-3 text-[10px] transition-colors md:justify-between md:px-3 md:text-sm ${
                isActive
                  ? 'bg-[#FFF0E5] text-primary font-black'
                  : 'text-muted hover:text-foreground hover:bg-[#FFFCFA]'
              }`
            }
          >
            <span className="flex flex-col items-center gap-1 md:flex-row md:gap-3">
              <item.icon className="w-4 h-4" />
              {item.label}
            </span>
            {item.to === '/monitor' && pendingReplies > 0 && (
              <span className="absolute right-1 top-2 h-2 w-2 rounded-full bg-danger md:static" aria-label="有待处理事项" />
            )}
          </NavLink>
        ))}
      </nav>

      <div className="space-y-3 border-t border-card-border px-2 py-4 md:px-4">
        <a
          href={GITHUB_URL}
          target="_blank"
          rel="noreferrer"
          aria-label="BossHunter GitHub"
          className="relative flex items-center justify-center rounded-xl border border-card-border bg-[#FFFCFA] px-3 py-3 text-xs font-black text-foreground transition-colors hover:border-primary/60 hover:text-primary md:rounded-2xl"
        >
          <Github className="h-4 w-4 shrink-0 md:absolute md:left-3" />
          <span className="mx-auto hidden items-center justify-center gap-2 md:flex">
            <span className="text-xl leading-none text-yellow-400">★</span>
            BossHunter
          </span>
        </a>
        <p className="hidden text-center text-[11px] leading-5 text-muted md:block">❤️  欢迎点 Star 支持维护  ❤️</p>
      </div>
    </aside>
  )
}
