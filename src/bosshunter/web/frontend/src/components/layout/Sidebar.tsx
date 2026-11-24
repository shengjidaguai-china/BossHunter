import { NavLink } from 'react-router-dom'
import { BriefcaseBusiness, Github, LayoutDashboard, Radar, Settings, PanelLeftClose, PanelLeftOpen, X } from 'lucide-react'
import { useEffect, useState } from 'react'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: '工作台' },
  { to: '/jobs', icon: BriefcaseBusiness, label: '岗位池' },
  { to: '/monitor', icon: Radar, label: '监测执行' },
  { to: '/config', icon: Settings, label: '配置' },
]

const GITHUB_URL = 'https://github.com/powerycy/BossHunter'

interface SidebarProps {
  onToggle?: () => void
  collapsed?: boolean
  mobileOpen?: boolean
  onNavigate?: () => void
  pendingReplies?: number
}

export function Sidebar({ collapsed = false, mobileOpen = false, onToggle, onNavigate, pendingReplies: pendingRepliesProp }: SidebarProps) {
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
    <aside data-mobile-open={mobileOpen} data-collapsed={collapsed} id="main-navigation" aria-label="主导航" className={`sidebar fixed inset-y-0 left-0 z-40 flex w-60 shrink-0 flex-col border-r border-card-border bg-card md:static motion-safe:transition-[width,transform] motion-safe:duration-300 motion-safe:ease-[cubic-bezier(0.22,1,0.36,1)] ${mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'} ${collapsed ? 'md:w-16' : 'md:w-60'}`}>
      <div className="relative flex h-16 shrink-0 items-center overflow-hidden border-b border-card-border px-3">
        <button type="button" onClick={collapsed ? onToggle : undefined}
          disabled={!collapsed} aria-label={collapsed ? '展开导航' : 'BossHunter'}
          aria-controls="main-navigation" aria-expanded={!collapsed} title={collapsed ? '展开导航' : undefined}
          className="sidebar-logo group relative flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg shadow-primary/20 focus-visible:outline focus-visible:outline-primary">
          <span className="sidebar-logo-text font-black text-sm motion-safe:transition-opacity motion-safe:duration-150">BH</span>
          <PanelLeftOpen className="sidebar-expand absolute h-5 w-5 opacity-0 motion-safe:transition-opacity motion-safe:duration-150" />
        </button>
        <div className="sidebar-label ml-3 whitespace-nowrap">
          <div className="font-black text-sm tracking-tight text-foreground">BossHunter</div>
          <div className="text-[11px] text-muted">v2.4.0 · 本地控制台</div>
        </div>
        <button type="button" onClick={onToggle} aria-label="收起导航" title="收起导航"
          aria-controls="main-navigation" aria-expanded={!collapsed}
          className="sidebar-collapse absolute right-2 hidden rounded-lg bg-card p-1.5 text-muted hover:bg-secondary hover:text-primary focus-visible:outline focus-visible:outline-primary md:block">
          <PanelLeftClose className="h-4 w-4" />
        </button>
        <button type="button" onClick={onToggle} aria-label="关闭导航" className="absolute right-2 rounded-lg bg-card p-2 text-muted md:hidden"><X size={18} /></button>
      </div>

      <nav className="flex-1 space-y-1 px-2 py-4 overflow-hidden">
        {navItems.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={onNavigate}
            aria-label={item.label}
            title={collapsed ? item.label : undefined}
            data-tour={item.to === '/config' ? 'nav-config' : item.to === '/' ? 'nav-workbench' : undefined}
            className={({ isActive }) =>
              `relative flex items-center justify-between gap-3 rounded-xl px-[15px] py-3 text-sm transition-colors ${
                isActive
                  ? 'bg-secondary text-primary font-black'
                  : 'text-muted hover:text-foreground hover:bg-surface'
              }`
            }
          >
            <span className="flex shrink-0 items-center gap-3">
              <item.icon className="w-4 h-4 shrink-0" />
              <span className="sidebar-label whitespace-nowrap">{item.label}</span>
            </span>
            {item.to === '/monitor' && pendingReplies > 0 && (
              <span className={`h-2 w-2 shrink-0 rounded-full bg-danger ${collapsed ? 'md:absolute md:right-1 md:top-2' : ''}`} aria-label="有待处理事项" />
            )}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer overflow-hidden border-t border-card-border px-2 py-4">
        <a
          href={GITHUB_URL}
          target="_blank"
          rel="noreferrer"
          aria-label="BossHunter GitHub"
          title="BossHunter GitHub"
          className="relative flex h-11 items-center justify-center overflow-hidden rounded-xl border border-card-border bg-surface text-xs font-black text-foreground transition-colors hover:border-primary/60 hover:text-primary md:rounded-2xl"
        >
          <Github className="absolute left-[15px] h-4 w-4 shrink-0" />
          <span className="sidebar-label absolute left-12 right-3 flex items-center justify-center gap-2 whitespace-nowrap">
            <span className="text-xl leading-none text-star">★</span>
            BossHunter
          </span>
        </a>
        <p className="sidebar-footer-caption sidebar-label whitespace-nowrap text-center text-[11px] leading-5 text-muted">❤️  欢迎点 Star 支持维护  ❤️</p>
      </div>
    </aside>
  )
}
