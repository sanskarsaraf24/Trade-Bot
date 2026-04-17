'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { configApi, authApi } from '@/lib/api'
import { useAuthStore } from '@/store/trading'
import Sidebar from '@/components/shared/Sidebar'
import { Save, RefreshCw, CheckCircle, AlertCircle, ExternalLink, Key } from 'lucide-react'
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

export default function ConfigPage() {
  const router = useRouter()
  const { token } = useAuthStore()
  const [loading, setLoading] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const [linking, setLinking] = useState(false)

  const { register, handleSubmit, reset, watch, formState: { isDirty }, getValues } = useForm<FormData>({
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

  useEffect(() => {
    if (!token) { router.push('/login'); return }
    configApi.get().then((res) => {
      const d = res.data
      reset({
        ...d,
        manual_symbols_text: (d.manual_symbols || []).join(','),
        nse_stocks: d.markets_enabled?.NSE_STOCKS ?? true,
        nse_options: d.markets_enabled?.NSE_OPTIONS ?? false,
      })
    }).catch(() => { /* no config yet — keep defaults */ })
  }, [token, router, reset])

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
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setError(err.response?.data?.detail || 'Save failed')
    } finally {
      setLoading(false)
    }
  }

  const handleLinkBroker = async () => {
    setLinking(true)
    try {
      // First save current API key/secret
      await onSubmit(getValues())
      
      const response = await axios.get('/api/auth/kite/login', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.data.login_url) {
        window.open(response.data.login_url, '_blank')
      }
    } catch (e) {
      setError('Failed to initiate broker link. Check API Key.')
    } finally {
      setLinking(false)
    }
  }

  return (
    <div className="flex h-screen overflow-hidden bg-surface-900">
      <Sidebar active="config" />
      <main className="flex-1 overflow-y-auto">
        <form onSubmit={handleSubmit(onSubmit)} className="p-6 max-w-3xl space-y-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-white">Bot Configuration</h1>
              <p className="text-xs text-slate-500 mt-1">Changes take effect on next bot start</p>
            </div>
            <div className="flex gap-2 items-center">
              {saved && (
                <span className="chip chip-profit">
                  <CheckCircle className="w-3 h-3" /> Saved
                </span>
              )}
              {error && (
                <span className="chip chip-loss text-xs">
                  <AlertCircle className="w-3 h-3" /> {error}
                </span>
              )}
              <button type="submit" disabled={loading} className="btn-primary disabled:opacity-50">
                {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Save Configuration
              </button>
            </div>
          </div>

          {/* Account */}
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

          {/* Trading Hours */}
          <section className="card space-y-4">
            <h2 className="text-sm font-semibold text-slate-200">Trading Hours</h2>
            <div className="grid grid-cols-3 gap-4">
              {[
                { id: 'market_start_time', label: 'Start Time' },
                { id: 'market_end_time', label: 'End Time' },
                { id: 'auto_exit_time', label: 'Auto-Exit At' },
              ].map(({ id, label }) => (
                <div key={id}>
                  <label className="block text-xs text-slate-400 mb-1">{label}</label>
                  <input id={id} type="time" {...register(id as keyof FormData)} className="form-input" />
                </div>
              ))}
            </div>
          </section>

          {/* Symbol Selection */}
          <section className="card space-y-4">
            <h2 className="text-sm font-semibold text-slate-200">Symbol Selection</h2>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Selection Mode</label>
              <select id="symbol_selection_mode" {...register('symbol_selection_mode')} className="form-input">
                <option value="auto">Auto (Claude chooses from list)</option>
                <option value="manual">Manual (specify symbols)</option>
              </select>
            </div>
            {selectionMode === 'manual' && (
              <div>
                <label className="block text-xs text-slate-400 mb-1">Stock Symbols (comma separated)</label>
                <input id="manual_symbols_text" type="text" placeholder="TCS,INFY,RELIANCE,SBIN"
                  {...register('manual_symbols_text')} className="form-input" />
              </div>
            )}
            {selectionMode === 'auto' && (
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
            <h2 className="text-sm font-semibold text-slate-200">Trading Parameters</h2>
            <div className="grid grid-cols-2 gap-4">
              {[
                { id: 'min_confidence_threshold', label: 'Min Confidence (%)', step: '1' },
                { id: 'max_concurrent_positions', label: 'Max Concurrent Positions', step: '1' },
                { id: 'analysis_interval_minutes', label: 'Analysis Interval (min)', step: '1' },
              ].map(({ id, label, step }) => (
                <div key={id}>
                  <label className="block text-xs text-slate-400 mb-1">{label}</label>
                  <input id={id} type="number" step={step}
                    {...register(id as keyof FormData, { valueAsNumber: true })} className="form-input" />
                </div>
              ))}
              <div>
                <label className="block text-xs text-slate-400 mb-1">Timeframe</label>
                <select id="timeframe" {...register('timeframe')} className="form-input">
                  {['scalp', 'intraday', 'swing'].map((v) => (
                    <option key={v} value={v}>{v.charAt(0).toUpperCase() + v.slice(1)}</option>
                  ))}
                </select>
              </div>
            </div>
          </section>

          {/* Broker */}
          <section className="card space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-sm font-semibold text-slate-200">Broker API Settings</h2>
              {brokerType === 'zerodha' && (
                <button
                  type="button"
                  onClick={handleLinkBroker}
                  disabled={linking}
                  className="text-xs flex items-center gap-1 text-brand-400 hover:text-brand-300 transition-colors"
                >
                  {linking ? <RefreshCw className="w-3 h-3 animate-spin" /> : <ExternalLink className="w-3 h-3" />}
                  Link Zerodha Account
                </button>
              )}
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Broker Type</label>
              <select id="broker_type" {...register('broker_type')} className="form-input">
                <option value="paper">Paper Trading (Simulation)</option>
                <option value="zerodha">Zerodha Kite</option>
              </select>
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
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1 flex items-center gap-1">
                  TOTP Secret Key <Key className="w-3 h-3 text-brand-500" />
                </label>
                <input id="broker_totp_secret" type="password" {...register('broker_totp_secret')}
                  placeholder="2FA Secret (e.g. ABCD123...)" className="form-input" />
                <p className="text-[10px] text-slate-500 mt-1">Leave empty if not using automatic 2FA login</p>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Access Token (Daily)</label>
                <input id="broker_access_token" type="password" {...register('broker_access_token')}
                  placeholder="Auto-filled after linking..." className="form-input" />
              </div>
            </div>
          </section>

          <div className="flex justify-end pb-8">
            <button type="submit" disabled={loading} className="btn-primary disabled:opacity-50">
              {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Save Configuration
            </button>
          </div>
        </form>
      </main>
    </div>
  )
}
