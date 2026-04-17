'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { authApi } from '@/lib/api'
import { useAuthStore } from '@/store/trading'
import { TrendingUp, Lock, Mail, AlertCircle } from 'lucide-react'

export default function LoginPage() {
  const router = useRouter()
  const setAuth = useAuthStore((s) => s.setAuth)

  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      // We use a fixed username for this single-user system
      const res = await authApi.login('admin@trade.system', password)
      const { access_token, user_id, email: userEmail } = res.data
      localStorage.setItem('trading_token', access_token)
      setAuth(access_token, user_id, userEmail)
      router.push('/')
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      setError(e.response?.data?.detail || 'Login failed. Check credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-900 px-4">
      {/* Background glow */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96
                        bg-brand-500/10 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-sm relative z-10 animate-fade-in">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-16 h-16 bg-brand-500/20 rounded-2xl flex items-center justify-center mb-4
                          border border-brand-500/30">
            <TrendingUp className="w-8 h-8 text-brand-400" />
          </div>
          <h1 className="text-2xl font-bold text-white">Trading Bot</h1>
          <p className="text-sm text-slate-400 mt-1">LLM-Powered · Indian Markets</p>
        </div>

        {/* Card */}
        <div className="card border-slate-700">
          <h2 className="text-lg font-semibold text-slate-100 mb-6">
            System Login
          </h2>

          {error && (
            <div className="flex items-center gap-2 bg-red-900/30 border border-red-800 rounded-lg
                            p-3 mb-4 text-sm text-red-300">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm text-slate-400 mb-2">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter system password"
                  required
                  autoFocus
                  className="form-input pl-9 h-12 text-lg"
                />
              </div>
            </div>

            <button
              id="submit-auth"
              type="submit"
              disabled={loading}
              className="btn-primary w-full h-12 justify-center disabled:opacity-50 text-base font-semibold"
            >
              {loading ? 'Please wait…' : 'Unlock Dashboard'}
            </button>
          </form>

          <p className="text-center text-xs text-slate-600 mt-6">
            This system is strictly private. Authorized access only.
          </p>
        </div>

        <p className="text-center text-xs text-slate-600 mt-6">
          trade.sanskarsaraf.in · Powered by Claude AI
        </p>
      </div>
    </div>
  )
}
