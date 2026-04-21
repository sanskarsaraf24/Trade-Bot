'use client'
import { useEffect, useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Sidebar from '@/components/shared/Sidebar'
import { configApi, authApi } from '@/lib/api'
import { useForm } from 'react-hook-form'
import { 
  Save, RefreshCw, AlertCircle, CheckCircle, Wallet, Shield, 
  Settings, Key, Link as LinkIcon, Activity, Braces, Layers
} from 'lucide-react'
import clsx from 'clsx'

const SECTORS = ['IT', 'Banking', 'Auto', 'Energy', 'Pharma', 'FMCG', 'Reality']

function ConfigForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [loading, setLoading] = useState(false)
  const [linking, setLinking] = useState(false)
  const [hasToken, setHasToken] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  const { register, handleSubmit, watch, setValue, reset } = useForm({
    defaultValues: {
      account_balance: 100000,
      risk_per_trade_percent: 1,
      max_daily_loss_percent: 5,
      broker_type: 'paper',
      broker_api_key: '',
      broker_api_secret: '',
      broker_totp_secret: '',
      broker_access_token: '',
      symbol_selection_mode: 'auto',
      manual_symbols_text: '',
      allowed_sectors: [],
      timeframe: 'intraday',
      min_confidence_threshold: 70,
      max_concurrent_positions: 3,
      analysis_interval_minutes: 15,
      system_instructions: '',
      require_manual_approval: false,
    }
  })

  useEffect(() => {
    if (searchParams.get('auth') === 'success') {
      setMessage({ type: 'success', text: 'Zerodha account linked successfully!' })
      setTimeout(() => setMessage(null), 5000)
    }
    configApi.get().then((res) => {
      const data = res.data
      setHasToken(!!data.broker_access_token)
      if (data.manual_symbols) {
        data.manual_symbols_text = data.manual_symbols.join(', ')
      }
      reset(data)
    })
  }, [reset, searchParams])

  const onSubmit = async (data: any) => {
    setLoading(true)
    try {
      const payload = { ...data }
      if (payload.manual_symbols_text) {
        payload.manual_symbols = payload.manual_symbols_text.split(',').map((s: string) => s.trim().toUpperCase())
      }
      if (typeof payload.max_daily_loss_percent === 'number' && Number.isFinite(payload.max_daily_loss_percent)) {
        payload.daily_loss_limit = (Number(payload.account_balance) * payload.max_daily_loss_percent) / 100
      }
      if (!Number.isFinite(payload.min_profit_absolute)) payload.min_profit_absolute = null
      if (!Number.isFinite(payload.min_profit_percent)) payload.min_profit_percent = null
      if (!payload.broker_api_key) delete payload.broker_api_key
      if (!payload.broker_api_secret) delete payload.broker_api_secret
      if (!payload.broker_access_token) delete payload.broker_access_token
      if (!payload.broker_totp_secret) delete payload.broker_totp_secret
      delete payload.manual_symbols_text
      await configApi.update(payload)
      setMessage({ type: 'success', text: 'Configuration saved successfully!' })
      setTimeout(() => setMessage(null), 5000)
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        'Failed to save configuration.'
      setMessage({ type: 'error', text: typeof detail === 'string' ? detail : 'Failed to save configuration.' })
    } finally {
      setLoading(false)
    }
  }

  const handleLinkBroker = async () => {
    setLinking(true)
    try {
      const res = await authApi.kiteLogin()
      window.location.href = res.data.login_url
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        'Failed to initialize Zerodha login'
      alert(typeof detail === 'string' ? detail : 'Failed to initialize Zerodha login')
      setLinking(false)
    }
  }

  const selectionMode = watch('symbol_selection_mode')
  const brokerType = watch('broker_type')

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="p-8 max-w-4xl mx-auto space-y-8 animate-in fade-in duration-500">
      
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-100 pb-8">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">System Configuration</h1>
          <p className="text-xs font-bold text-slate-400 mt-1 uppercase tracking-widest">Global parameters & strategy control</p>
        </div>
        {message && (
          <div className={clsx(
            'flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold animate-in slide-in-from-top-2',
            message.type === 'success' ? 'bg-emerald-50 text-emerald-600 border border-emerald-100' : 'bg-rose-50 text-rose-600 border border-rose-100'
          )}>
            {message.type === 'success' ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
            {message.text}
          </div>
        )}
      </div>

      {/* Risk Management */}
      <section className="space-y-4">
        <h2 className="section-title"><Wallet className="w-3.5 h-3.5" /> Treasury & Risk</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="card border-none shadow-soft">
            <label className="stat-label mb-2 block">Account Equity (₹)</label>
            <input id="account_balance" type="number" {...register('account_balance', { valueAsNumber: true })} className="form-input font-mono font-bold" />
          </div>
          <div className="card border-none shadow-soft">
            <label className="stat-label mb-2 block text-indigo-600">Risk per Trade (%)</label>
            <input id="risk_per_trade_percent" type="number" step="0.1" {...register('risk_per_trade_percent', { valueAsNumber: true })} className="form-input font-mono font-bold" />
          </div>
          <div className="card border-none shadow-soft">
            <label className="stat-label mb-2 block text-rose-600">Daily Stop Loss (%)</label>
            <input id="max_daily_loss_percent" type="number" step="0.1" {...register('max_daily_loss_percent', { valueAsNumber: true })} className="form-input font-mono font-bold" />
          </div>
        </div>
      </section>

      {/* Broker API Settings */}
      <section className="space-y-4">
        <div className="flex justify-between items-center mb-2">
            <h2 className="section-title !mb-0"><Shield className="w-3.5 h-3.5" /> Broker Gateway</h2>
            {brokerType === 'zerodha' && (
                <button type="button" onClick={handleLinkBroker} disabled={linking}
                    className="flex items-center gap-2 px-4 py-2 bg-indigo-50 hover:bg-indigo-100 text-indigo-600 rounded-xl text-[10px] font-black uppercase tracking-widest border border-indigo-100 transition-all shadow-sm">
                    {linking ? <RefreshCw className="w-3 h-3 animate-spin" /> : <LinkIcon className="w-3 h-3" />}
                    Re-link Zerodha
                </button>
            )}
        </div>
        
        <div className="card border-none shadow-soft space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                    <label className="stat-label mb-2 block">Execution Environment</label>
                    <select id="broker_type" {...register('broker_type')} className="form-input font-bold">
                        <option value="paper">Simulator (Paper Trading)</option>
                        <option value="zerodha">Zerodha Kite (Production)</option>
                    </select>
                </div>
                <div>
                    <label className="stat-label mb-2 block">TOTP Secret Key</label>
                    <div className="relative">
                        <Key className="w-3.5 h-3.5 absolute left-3.5 top-3.5 text-slate-300" />
                        <input id="broker_totp_secret" type="password" {...register('broker_totp_secret')}
                            placeholder="32-Character Secret" className="form-input pl-10" />
                    </div>
                </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                    <label className="stat-label mb-2 block text-slate-400">API Key</label>
                    <input id="broker_api_key" type="password" {...register('broker_api_key')}
                        placeholder="••••••••••••••••" className="form-input" />
                </div>
                <div>
                    <label className="stat-label mb-2 block text-slate-400">API Secret</label>
                    <input id="broker_api_secret" type="password" {...register('broker_api_secret')}
                        placeholder="••••••••••••••••" className="form-input" />
                </div>
            </div>
            
            <div className="bg-slate-50 p-6 rounded-2xl border border-slate-100">
                <label className="stat-label mb-3 block">Autonomous Authentication</label>
                <div className="flex items-center gap-4">
                    <div className="flex-1 relative">
                        <input id="broker_access_token" type="password" {...register('broker_access_token')}
                            disabled={true}
                            placeholder={hasToken ? "AUTHENTICATED" : "NOT LINKED"} 
                            className={clsx(
                                "form-input !py-3 tracking-widest text-center !bg-white",
                                hasToken ? "text-emerald-600" : "text-slate-400"
                            )}
                        />
                        {hasToken && <CheckCircle className="w-4 h-4 text-emerald-500 absolute right-4 top-3.5" />}
                    </div>
                    {hasToken ? (
                        <div className="flex items-center gap-2 text-[10px] font-bold text-emerald-600 uppercase tracking-widest px-4 py-2.5 bg-emerald-50 rounded-xl border border-emerald-100">
                            Valid Session
                        </div>
                    ) : (
                        <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest px-4 py-2.5 bg-slate-100 rounded-xl">
                            Missing Token
                        </div>
                    )}
                </div>
            </div>
        </div>
      </section>

      {/* Execution Logic */}
      <section className="space-y-4">
        <h2 className="section-title"><Braces className="w-3.5 h-3.5" /> High-Level Strategy</h2>
        <div className="card border-none shadow-soft space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                    <label className="stat-label mb-2 block">Universe Selection</label>
                    <select id="symbol_selection_mode" {...register('symbol_selection_mode')} className="form-input font-bold">
                        <option value="auto">Claude Engine (Automated)</option>
                        <option value="manual">Portfolio Restricted (Manual)</option>
                    </select>
                </div>
                <div>
                    <label className="stat-label mb-2 block">Trade Window</label>
                    <select id="timeframe" {...register('timeframe')} className="form-input font-bold">
                        <option value="scalp">Scalping (Quick Exit)</option>
                        <option value="intraday" selected>Intraday (Standard)</option>
                        <option value="swing">Swing (Multi-day)</option>
                    </select>
                </div>
            </div>

            {selectionMode === 'manual' ? (
            <div>
                <label className="stat-label mb-2 block">Fitted List (CSV)</label>
                <input id="manual_symbols_text" type="text" placeholder="TCS, RELIANCE, INFY..."
                {...register('manual_symbols_text')} className="form-input font-mono text-xs" />
            </div>
            ) : (
            <div>
                <label className="stat-label mb-3 block">Permitted Sectors</label>
                <div className="flex flex-wrap gap-2">
                    {SECTORS.map((s) => (
                        <label key={s} className="group relative cursor-pointer flex items-center gap-2 px-3 py-2 bg-slate-50 hover:bg-slate-100 rounded-lg border border-slate-100 transition-all">
                            <input type="checkbox" value={s} {...register('allowed_sectors')} className="accent-indigo-600" />
                            <span className="text-[11px] font-bold text-slate-600 uppercase tracking-wider">{s}</span>
                        </label>
                    ))}
                </div>
            </div>
            )}
        </div>
      </section>

      {/* Bot Parameters */}
      <section className="space-y-4">
        <h2 className="section-title"><Settings className="w-3.5 h-3.5" /> Engine Tuning</h2>
        <div className="card border-none shadow-soft grid grid-cols-1 md:grid-cols-3 gap-6">
           <div>
              <label className="stat-label mb-2 block">Min Confidence (%)</label>
              <input id="min_confidence_threshold" type="number" 
                {...register('min_confidence_threshold', { valueAsNumber: true })} className="form-input font-bold" />
            </div>
            <div>
              <label className="stat-label mb-2 block">Global Slot Limit</label>
              <input id="max_concurrent_positions" type="number"
                {...register('max_concurrent_positions', { valueAsNumber: true })} className="form-input font-bold" />
            </div>
            <div>
              <label className="stat-label mb-2 block">Analysis Sweep (min)</label>
              <input id="analysis_interval_minutes" type="number"
                {...register('analysis_interval_minutes', { valueAsNumber: true })} className="form-input font-bold" />
            </div>
        </div>
      </section>

      {/* Advanced AI */}
      <section className="space-y-4">
        <h2 className="section-title"><Layers className="w-3.5 h-3.5" /> Semantic Guardrails</h2>
        <div className="card border-none shadow-soft space-y-4">
            <textarea
            id="system_instructions"
            rows={4}
            placeholder="Set specific mandates for Claude (e.g. 'Prioritize mean reversion in overbought sectors')..."
            {...register('system_instructions')}
            className="form-input resize-none bg-slate-50 !border-dashed"
            />
            <label className="flex items-center gap-3 p-4 bg-indigo-50/30 rounded-2xl border border-indigo-100/50 cursor-pointer hover:bg-indigo-50/50 transition-colors">
                <input type="checkbox" id="require_manual_approval"
                    {...register('require_manual_approval')} className="w-4 h-4 accent-indigo-600" />
                <div>
                    <p className="text-xs font-bold text-slate-900 uppercase tracking-widest leading-none mb-1">Gatekeeper Mode</p>
                    <p className="text-[10px] font-medium text-slate-500 uppercase tracking-tighter">AI will generate signals but wait for your click before firing orders</p>
                </div>
            </label>
        </div>
      </section>

      <div className="flex justify-end pb-12 pt-4">
        <button type="submit" disabled={loading} className="btn-primary w-full md:w-auto px-12 py-4 text-[11px] font-black uppercase tracking-[0.2em] shadow-lg shadow-indigo-600/20">
          {loading ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
          Apply Global Config
        </button>
      </div>
    </form>
  )
}

export default function ConfigPage() {
  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <Sidebar active="config" />
      <main className="flex-1 overflow-y-auto">
        <Suspense fallback={<div className="p-8 text-slate-400 font-bold uppercase tracking-widest text-[11px] animate-pulse">Syncing Engine Config...</div>}>
          <ConfigForm />
        </Suspense>
      </main>
    </div>
  )
}
