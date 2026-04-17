'use client'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/trading'
import {
  LayoutDashboard, Settings, BarChart2, TrendingUp, LogOut, User as UserIcon
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
    <aside className="w-64 shrink-0 flex flex-col bg-white border-r border-slate-200 h-screen shadow-sm">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-8">
        <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
          <TrendingUp className="w-5 h-5 text-white" />
        </div>
        <div>
          <p className="text-base font-bold text-slate-900 tracking-tight leading-none">TradingBot</p>
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">Intelligence</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const isActive = (active === 'dashboard' && href === '/') ||
                           (active === label.toLowerCase())
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                'flex items-center gap-3 px-4 py-3 rounded-xl text-sm transition-all duration-200 group',
                isActive
                  ? 'bg-indigo-50 text-indigo-600 font-bold'
                  : 'text-slate-500 hover:text-slate-900 hover:bg-slate-50'
              )}
            >
              <Icon className={clsx('w-5 h-5 shrink-0 transition-transform duration-200', !isActive && 'group-hover:scale-110')} />
              {label}
            </Link>
          )
        })}
      </nav>

      {/* User Footer */}
      <div className="mx-3 my-6 p-4 bg-slate-50 rounded-2xl border border-slate-100">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-full bg-white flex items-center justify-center border border-slate-200 text-slate-400">
            <UserIcon className="w-4 h-4" />
          </div>
          <div className="overflow-hidden">
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest leading-none">Account</p>
            <p className="text-[11px] font-semibold text-slate-900 truncate mt-1">{email}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="w-full flex items-center justify-center gap-2 py-2 text-[11px] font-bold text-slate-500 hover:text-rose-600 hover:bg-rose-50 transition-all duration-200 rounded-xl uppercase tracking-widest border border-transparent hover:border-rose-100"
        >
          <LogOut className="w-3.5 h-3.5" /> Sign out
        </button>
      </div>
    </aside>
  )
}
