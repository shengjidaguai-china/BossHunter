import { NavLink } from 'react-router-dom'
import { BriefcaseBusiness, LayoutDashboard, Radar, Settings } from 'lucide-react'
import { useEffect, useState } from 'react'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: '工作台' },
  { to: '/jobs', icon: BriefcaseBusiness, label: '岗位池' },
  { to: '/monitor', icon: Radar, label: '监测执行' },
  { to: '/config', icon: Settings, label: '配置' },
]

export function MobileTabBar() {
  const [pendingReplies, setPendingReplies] = useState(0)

  useEffect(() => {
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
  }, [])

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 flex h-16 items-center justify-around border-t border-card-border bg-white/95 px-2 backdrop-blur-md md:hidden safe-area-pb">
      {navItems.map(item => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            `relative flex flex-col items-center justify-center py-1 px-3 text-xs font-bold transition-colors ${
              isActive ? 'text-primary' : 'text-muted hover:text-foreground'
            }`
          }
        >
          <div className="relative">
            <item.icon className="h-5 w-5" />
            {item.to === '/monitor' && pendingReplies > 0 && (
              <span className="absolute -top-1 -right-1.5 h-2.5 w-2.5 rounded-full bg-danger ring-2 ring-white" />
            )}
          </div>
          <span className="mt-1 text-[11px] leading-tight">{item.label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
