import { NavLink, Outlet } from 'react-router-dom'
import {
  Activity,
  Box,
  Container,
  LayoutDashboard,
  Layers,
  Server,
  Settings,
  Workflow,
  Zap,
} from 'lucide-react'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/nodes', icon: Server, label: 'Nodes' },
  { to: '/services', icon: Layers, label: 'Services' },
  { to: '/containers', icon: Container, label: 'Containers' },
  { to: '/kubernetes', icon: Box, label: 'Kubernetes' },
  { to: '/jobs', icon: Workflow, label: 'Jobs' },
  { to: '/activity', icon: Activity, label: 'Activity Log' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export function AppLayout() {
  return (
    <div className="flex min-h-screen">
      <aside className="w-64 bg-surface-raised border-r border-border flex flex-col fixed h-full z-10">
        <div className="px-6 py-5 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-accent/20 flex items-center justify-center">
              <Zap size={20} className="text-accent" />
            </div>
            <div>
              <h1 className="font-bold text-white text-lg leading-tight">OpsDeck</h1>
              <p className="text-xs text-gray-500">HomeLab Manager</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-accent/15 text-accent'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-surface-overlay'
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="px-6 py-4 border-t border-border">
          <p className="text-xs text-gray-500">v0.1.0 · MVP</p>
        </div>
      </aside>

      <main className="flex-1 ml-64 p-6 lg:p-8">
        <Outlet />
      </main>
    </div>
  )
}
