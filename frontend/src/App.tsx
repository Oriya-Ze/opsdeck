import { Route, Routes } from 'react-router-dom'
import { AppLayout } from './layouts/AppLayout'
import { DashboardPage } from './pages/DashboardPage'
import { NodesPage } from './pages/NodesPage'
import { NodeDetailPage } from './pages/NodeDetailPage'
import { ServicesPage } from './pages/ServicesPage'
import { ContainersPage } from './pages/ContainersPage'
import { KubernetesPage } from './pages/KubernetesPage'
import { JobsPage } from './pages/JobsPage'
import { PlaybooksPage } from './pages/PlaybooksPage'
import { ActivityLogPage } from './pages/ActivityLogPage'
import { MonitoringPage } from './pages/MonitoringPage'
import { SettingsPage } from './pages/SettingsPage'
import { TerminalPage } from './pages/TerminalPage'

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="nodes" element={<NodesPage />} />
        <Route path="nodes/:id" element={<NodeDetailPage />} />
        <Route path="services" element={<ServicesPage />} />
        <Route path="containers" element={<ContainersPage />} />
        <Route path="kubernetes" element={<KubernetesPage />} />
        <Route path="jobs" element={<JobsPage />} />
        <Route path="playbooks" element={<PlaybooksPage />} />
        <Route path="activity" element={<ActivityLogPage />} />
        <Route path="monitoring" element={<MonitoringPage />} />
        <Route path="terminal" element={<TerminalPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  )
}
