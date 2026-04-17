'use client'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/trading'
import {
  LayoutDashboard, Settings, BarChart2, TrendingUp, LogOut
} from 'lucide-react'
import clsx from 'clsx'

const NAV = [
  { href: '/',           label: 'Dashboard', icon: LayoutDashboard },
  { href: '/config',     label: 'Config',    icon: Settings },
  { href: '/analytics',  label: 'Analytics', icon: BarChart2 },
]

export default function Sidebar({ active }: { active: string }) {
  const router = useRouter()
  const { logout, email } = useAuthStore()

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  return (
    <aside className="w-56 shrink-0 flex flex-col bg-surface-850 border-r border-slate-800 h-screen">
      {/* Logo */}
      <div className="flex items-center gap-2 px-4 py-5 border-b border-slate-800">
        <div className="w-8 h-8 bg-brand-500 rounded-lg flex items-center justify-center">
          <TrendingUp className="w-4 h-4 text-white" />
        </div>
        <div>
          <p className="text-sm font-bold text-white leading-none">TradingBot</p>
          <p className="text-[10px] text-slate-500">Claude AI</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-4 space-y-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const isActive = (active === 'dashboard' && href === '/') ||
                           (href !== '/' && active === label.toLowerCase())
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                isActive
                  ? 'bg-brand-500/15 text-brand-400 font-medium'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              )}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </Link>
          )
        })}
      </nav>

      {/* User */}
      <div className="px-4 py-4 border-t border-slate-800">
        <p className="text-xs text-slate-500 truncate mb-2">{email}</p>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 text-xs text-slate-500 hover:text-red-400 transition-colors"
        >
          <LogOut className="w-3.5 h-3.5" /> Sign out
        </button>
      </div>
    </aside>
  )
}
