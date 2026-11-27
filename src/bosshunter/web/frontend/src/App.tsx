import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Sidebar } from './components/layout/Sidebar'
import { Header } from './components/layout/Header'
import DashboardPage from './pages/DashboardPage'
import ConfigPage from './pages/ConfigPage'
import { OnboardingTour } from './components/onboarding/OnboardingTour'

function JobsPage() {
  return <DashboardPage view="jobs" />
}

function MonitorPage() {
  return <DashboardPage view="monitor" />
}

export default function App() {
  const [collapsed, setCollapsed] = useState(() => {
    try {
      const saved = localStorage.getItem('bosshunter.sidebar.collapsed')
      if (saved === 'true' || saved === 'false') return saved === 'true'
    } catch { /* Storage can be unavailable in private browsing. */ }
    return window.innerWidth < 1280
  })
  const [mobileOpen, setMobileOpen] = useState(false)
  useEffect(() => {
    if (!mobileOpen) return
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMobileOpen(false)
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [mobileOpen])
  const toggleNavigation = () => {
    if (window.innerWidth < 768) {
      setMobileOpen(value => !value)
      return
    }
    const next = !collapsed
    setCollapsed(next)
    try { localStorage.setItem('bosshunter.sidebar.collapsed', String(next)) } catch { /* Keep in-memory preference. */ }
  }
  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden bg-background text-foreground">
        {mobileOpen && <button type="button" aria-label="关闭导航" onClick={() => setMobileOpen(false)} className="fixed inset-0 z-30 bg-black/40 md:hidden" />}
        <Sidebar collapsed={collapsed} mobileOpen={mobileOpen} onToggle={toggleNavigation} onNavigate={() => setMobileOpen(false)} />
        <div className="min-w-0 flex-1 flex flex-col overflow-hidden">
          <Header mobileOpen={mobileOpen} onToggle={toggleNavigation} />
          <main className="min-w-0 flex-1 overflow-y-auto p-3 md:p-6">
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/jobs" element={<JobsPage />} />
              <Route path="/monitor" element={<MonitorPage />} />
              <Route path="/config" element={<ConfigPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
        <OnboardingTour />
      </div>
    </BrowserRouter>
  )
}
