'use client'
import { useEffect, useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { configApi } from '@/lib/api'
import { useAuthStore } from '@/store/trading'
import Sidebar from '@/components/shared/Sidebar'
import { Save, RefreshCw, CheckCircle, AlertCircle, ExternalLink, Key, Link as LinkIcon } from 'lucide-react'
import axios from 'axios'

const SECTORS = ['IT', 'Banking', 'Auto', 'Pharma', 'FMCG', 'Metals', 'Energy', 'Telecom', 'Infra']
const STRATEGIES = ['Breakouts', 'Mean Reversion', 'Trend Following', 'Options Volatility']
const AVOID = ['Earnings Week', 'RBI Announcements', 'First 15 min', 'High Volatility']

type FormData = {
  account_balance: number
  daily_profit_target: number
  daily_loss_limit: number
  risk_per_trade_percent: number
  risk_appetite: string
  market_start_time: string
  market_end_time: string
  auto_exit_time: string
  symbol_selection_mode: string
  manual_symbols_text: string
  min_confidence_threshold: number
  max_concurrent_positions: number
  timeframe: string
  analysis_interval_minutes: number
  require_manual_approval: boolean
  system_instructions: string
  broker_type: string
  broker_api_key: string
  broker_api_secret: string
  broker_access_token: string
  broker_totp_secret: string
  email_alerts_enabled: boolean
  alert_email: string
  allowed_sectors: string[]
  enabled_strategies: string[]
  avoid_trading_during: string[]
  nse_stocks: boolean
  nse_options: boolean
}

function ConfigForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { token } = useAuthStore()
  const [loading, setLoading] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const [linking, setLinking] = useState(false)

  const { register, handleSubmit, reset, watch, getValues, setValue } = useForm<FormData>({
    defaultValues: {
      account_balance: 1000000,
      daily_profit_target: 25000,
      daily_loss_limit: 20000,
      risk_per_trade_percent: 1.0,
      risk_appetite: 'moderate',
      market_start_time: '09:15',
      market_end_time: '15:15',
      auto_exit_time: '15:25',
      symbol_selection_mode: 'auto',
      manual_symbols_text: 'TCS,INFY,RELIANCE',
      min_confidence_threshold: 65,
      max_concurrent_positions: 5,
      timeframe: 'intraday',
      analysis_interval_minutes: 15,
      require_manual_approval: false,
      system_instructions: '',
      broker_type: 'paper',
      broker_api_key: '',
      broker_api_secret: '',
      broker_access_token: '',
      broker_totp_secret: '',
      email_alerts_enabled: true,
      alert_email: '',
      allowed_sectors: ['IT', 'Banking'],
      enabled_strategies: ['Breakouts', 'Trend Following'],
      avoid_trading_during: ['Earnings Week', 'RBI Announcements', 'First 15 min'],
      nse_stocks: true,
      nse_options: false,
    },
  })

  const selectionMode = watch('symbol_selection_mode')
  const brokerType = watch('broker_type')
  const hasToken = !!watch('broker_access_token')

  const fetchConfig = async () => {
    try {
      const res = await configApi.get()
      const d = res.data
      reset({
        ...d,
        manual_symbols_text: (d.manual_symbols || []).join(','),
        nse_stocks: d.markets_enabled?.NSE_STOCKS ?? true,
        nse_options: d.markets_enabled?.NSE_OPTIONS ?? false,
      })
    } catch (err) {
      console.error('Failed to fetch config', err)
    }
  }

  useEffect(() => {
    if (!token) { router.push('/login'); return }
    fetchConfig()
  }, [token, router])

  useEffect(() => {
    const authStatus = searchParams.get('auth')
    if (authStatus === 'success') {
      setSaved(true)
      setTimeout(() => setSaved(false), 5000)
      fetchConfig()
      // Clean URL
      window.history.replaceState({}, '', '/config')
    } else if (authStatus === 'error') {
      setError(`Authentication failed: ${searchParams.get('reason') || 'Unknown error'}`)
      window.history.replaceState({}, '', '/config')
    }
  }, [searchParams])

  const onSubmit = async (data: FormData) => {
    setLoading(true); setSaved(false); setError('')
    try {
      const payload = {
        ...data,
        manual_symbols: data.manual_symbols_text
          .split(',').map((s) => s.trim().toUpperCase()).filter(Boolean),
        markets_enabled: {
          NSE_STOCKS: data.nse_stocks,
          NSE_OPTIONS: data.nse_options,
        },
      }
      await configApi.save(payload)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Save failed')
    } finally {
      setLoading(false)
    }
  }

  const handleLinkBroker = async () => {
    setLinking(true)
    setError('')
    try {
      // Save current keys first
      await onSubmit(getValues())
      
      const API_URL = process.env.NEXT_PUBLIC_API_URL || '/api'
      const response = await axios.get(`${API_URL}/auth/kite/login`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.data.login_url) {
        window.location.href = response.data.login_url
      }
    } catch (e) {
      setError('Connection failed. Check your API Key and Secret.')
    } finally {
      setLinking(false)
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="p-6 max-w-3xl space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Bot Configuration</h1>
          <p className="text-xs text-slate-500 mt-1">Changes take effect on next bot start</p>
        </div>
        <div className="flex gap-2 items-center">
          {saved && (
            <span className="chip chip-profit animate-in fade-in slide-in-from-top-1">
              <CheckCircle className="w-3 h-3" /> Config Saved
            </span>
          )}
          {error && (
            <span className="chip chip-loss text-xs animate-in fade-in slide-in-from-top-1">
              <AlertCircle className="w-3 h-3" /> {error}
            </span>
          )}
          <button type="submit" disabled={loading} className="btn-primary disabled:opacity-50">
            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Save Configuration
          </button>
        </div>
      </div>

      {/* Account & Risk */}
      <section className="card space-y-4">
        <h2 className="text-sm font-semibold text-slate-200">Account & Risk</h2>
        <div className="grid grid-cols-2 gap-4">
          {[
            { id: 'account_balance', label: 'Available Funds (₹)', type: 'number' },
            { id: 'daily_profit_target', label: 'Daily Profit Target (₹)', type: 'number' },
            { id: 'daily_loss_limit', label: 'Daily Loss Limit (₹)', type: 'number' },
            { id: 'risk_per_trade_percent', label: 'Risk Per Trade (%)', type: 'number', step: '0.1' },
          ].map(({ id, label, type, step }) => (
            <div key={id}>
              <label className="block text-xs text-slate-400 mb-1">{label}</label>
              <input id={id} type={type} step={step} {...register(id as keyof FormData, { valueAsNumber: true })}
                className="form-input" />
            </div>
          ))}
        </div>
        <div>
          <label className="block text-xs text-slate-400 mb-1">Risk Appetite</label>
          <select id="risk_appetite" {...register('risk_appetite')} className="form-input">
            {['conservative', 'moderate', 'aggressive'].map((v) => (
              <option key={v} value={v}>{v.charAt(0).toUpperCase() + v.slice(1)}</option>
            ))}
          </select>
        </div>
      </section>

      {/* Broker API Settings */}
      <section className="card space-y-4 border border-brand-500/10">
        <div className="flex justify-between items-center">
          <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            Broker Gateway
            {hasToken && (
              <span className="bg-emerald-500/10 text-emerald-500 text-[10px] px-1.5 py-0.5 rounded border border-emerald-500/20 flex items-center gap-1">
                <CheckCircle className="w-2.5 h-2.5" /> Linked
              </span>
            )}
          </h2>
          {brokerType === 'zerodha' && (
            <button
              type="button"
              onClick={handleLinkBroker}
              disabled={linking}
              className="text-xs flex items-center gap-1.5 text-brand-400 hover:text-brand-300 transition-colors bg-brand-500/5 px-3 py-1.5 rounded border border-brand-500/20"
            >
              {linking ? <RefreshCw className="w-3 h-3 animate-spin" /> : <LinkIcon className="w-3 h-3" />}
              Re-link Zerodha
            </button>
          )}
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Exchange Broker</label>
            <select id="broker_type" {...register('broker_type')} className="form-input">
              <option value="paper">Paper Trading (Simulation)</option>
              <option value="zerodha">Zerodha Kite</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1 flex items-center gap-1">
              TOTP Secret Key <Key className="w-3 h-3 text-brand-500" />
            </label>
            <input id="broker_totp_secret" type="password" {...register('broker_totp_secret')}
              placeholder="ABCD..." className="form-input" />
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-slate-400 mb-1">API Key</label>
            <input id="broker_api_key" type="password" {...register('broker_api_key')}
              placeholder="••••••••" className="form-input" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">API Secret</label>
            <input id="broker_api_secret" type="password" {...register('broker_api_secret')}
              placeholder="••••••••" className="form-input" />
          </div>
        </div>
        
        <div>
          <label className="block text-xs text-slate-400 mb-1">Active Session Token (Auto-filled)</label>
          <div className="relative">
            <input id="broker_access_token" type="password" 
              {...register('broker_access_token')}
              disabled={true}
              placeholder={hasToken ? "Session Active ✅" : "Click Link Zerodha to generate..."} 
              className="form-input pr-10 bg-slate-800/50 cursor-not-allowed opacity-70" 
            />
            {hasToken && <CheckCircle className="w-4 h-4 text-emerald-500 absolute right-3 top-2.5" />}
          </div>
          <p className="text-[10px] text-slate-500 mt-1.5 px-1">
            Valid until next market day. The bot will use your TOTP secret to auto-refresh this daily.
          </p>
        </div>
      </section>

      {/* Symbol Selection */}
      <section className="card space-y-4">
        <h2 className="text-sm font-semibold text-slate-200">Execution Strategy</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Selection Mode</label>
            <select id="symbol_selection_mode" {...register('symbol_selection_mode')} className="form-input">
              <option value="auto">Auto (AI Controlled)</option>
              <option value="manual">Manual Portfolio</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Timeframe</label>
            <select id="timeframe" {...register('timeframe')} className="form-input">
              {['scalp', 'intraday', 'swing'].map((v) => (
                <option key={v} value={v}>{v.charAt(0).toUpperCase() + v.slice(1)}</option>
              ))}
            </select>
          </div>
        </div>

        {selectionMode === 'manual' ? (
          <div>
            <label className="block text-xs text-slate-400 mb-1">Stock Symbols</label>
            <input id="manual_symbols_text" type="text" placeholder="TCS, RELIANCE..."
              {...register('manual_symbols_text')} className="form-input" />
          </div>
        ) : (
          <div>
            <label className="block text-xs text-slate-400 mb-2">Allowed Sectors</label>
            <div className="flex flex-wrap gap-2">
              {SECTORS.map((s) => (
                <label key={s} className="flex items-center gap-1.5 cursor-pointer">
                  <input type="checkbox" value={s} {...register('allowed_sectors')}
                    className="accent-brand-500" />
                  <span className="text-xs text-slate-300">{s}</span>
                </label>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* Parameters */}
      <section className="card space-y-4">
        <h2 className="text-sm font-semibold text-slate-200">Gate Controls</h2>
        <div className="grid grid-cols-3 gap-4">
           <div>
              <label className="block text-xs text-slate-400 mb-1">Min Conf (%)</label>
              <input id="min_confidence_threshold" type="number" 
                {...register('min_confidence_threshold', { valueAsNumber: true })} className="form-input" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Max Positions</label>
              <input id="max_concurrent_positions" type="number"
                {...register('max_concurrent_positions', { valueAsNumber: true })} className="form-input" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Interval (min)</label>
              <input id="analysis_interval_minutes" type="number"
                {...register('analysis_interval_minutes', { valueAsNumber: true })} className="form-input" />
            </div>
        </div>
      </section>

      {/* Advanced */}
      <section className="card space-y-4">
        <h2 className="text-sm font-semibold text-slate-200">Advanced Instructions</h2>
        <textarea
          id="system_instructions"
          rows={3}
          placeholder="Favor mean reversion in choppy markets..."
          {...register('system_instructions')}
          className="form-input resize-none"
        />
        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" id="require_manual_approval"
            {...register('require_manual_approval')} className="accent-brand-500" />
          <span className="text-sm text-slate-300">Require manual approval for each trade</span>
        </label>
      </section>

      <div className="flex justify-end pb-12">
        <button type="submit" disabled={loading} className="btn-primary">
          {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          Save All Changes
        </button>
      </div>
    </form>
  )
}

export default function ConfigPage() {
  return (
    <div className="flex h-screen overflow-hidden bg-surface-900">
      <Sidebar active="config" />
      <main className="flex-1 overflow-y-auto">
        <Suspense fallback={<div className="p-6 text-slate-500">Loading Configuration...</div>}>
          <ConfigForm />
        </Suspense>
      </main>
    </div>
  )
}
