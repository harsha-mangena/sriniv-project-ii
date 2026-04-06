import { NavLink } from 'react-router-dom'
import { LayoutDashboard, MessageSquare, BookOpen, BarChart3, Radio, Settings } from 'lucide-react'
import clsx from 'clsx'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/mock', icon: MessageSquare, label: 'Mock Interview' },
  { to: '/prep', icon: BookOpen, label: 'Prep Mode' },
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
  { to: '/realtime', icon: Radio, label: 'Real-Time' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Sidebar() {
  return (
    <aside className="w-64 bg-navy-800 border-r border-navy-700 flex flex-col">
      <div className="p-6 border-b border-navy-700">
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <span className="w-8 h-8 bg-accent rounded-lg flex items-center justify-center text-sm font-bold">IP</span>
          InterviewPilot
        </h1>
        <p className="text-xs text-gray-500 mt-1">AoT + ToT Hybrid Engine</p>
      </div>
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-accent/10 text-accent'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-navy-700'
              )
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="p-4 border-t border-navy-700">
        <p className="text-xs text-gray-500">AI Interview Coach</p>
        <p className="text-xs text-gray-500">Ollama / Gemini</p>
      </div>
    </aside>
  )
}
