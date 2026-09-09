import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Sidebar } from './components/layout/Sidebar'
import { Header } from './components/layout/Header'
import { MobileTabBar } from './components/layout/MobileTabBar'
import DashboardPage from './pages/DashboardPage'
import ConfigPage from './pages/ConfigPage'

function JobsPage() {
  return <DashboardPage view="jobs" />
}

function MonitorPage() {
  return <DashboardPage view="monitor" />
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden bg-background text-foreground">
        <Sidebar />
        <div className="min-w-0 flex-1 flex flex-col overflow-hidden relative">
          <Header />
          <main className="min-w-0 flex-1 overflow-y-auto p-3 sm:p-4 md:p-6 pb-20 md:pb-6">
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/jobs" element={<JobsPage />} />
              <Route path="/monitor" element={<MonitorPage />} />
              <Route path="/config" element={<ConfigPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
          <MobileTabBar />
        </div>
      </div>
    </BrowserRouter>
  )
}
