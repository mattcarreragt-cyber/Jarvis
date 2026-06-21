'use client'

import { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { MonitorPlay, X, Power, ShieldHalf, Loader2, RefreshCw } from 'lucide-react'
import { remoteWake, remoteStatus, vpnStatus, vpnControl } from '@/lib/api'

interface Props { onClose: () => void }

export default function RemotePanel({ onClose }: Props) {
  const [sun, setSun] = useState<{ up: boolean; host: string } | null>(null)
  const [waking, setWaking] = useState(false)
  const [vpn, setVpn] = useState<{ protected: boolean; ip?: string; loc?: string; ssh?: string | null } | null>(null)

  const loadSun = useCallback(async () => {
    const s = await remoteStatus(); setSun({ up: s.sunshine_up, host: s.host })
  }, [])
  const loadVpn = useCallback(async () => {
    const v = await vpnStatus()
    const h = v.http_status as Record<string, unknown> | null
    setVpn({
      protected: Boolean(h?.mullvad_exit_ip),
      ip: h?.ip as string | undefined,
      loc: h ? `${h.city ?? '?'}, ${h.country ?? '?'}` : undefined,
      ssh: v.ssh_status,
    })
  }, [])

  useEffect(() => { loadSun(); loadVpn() }, [loadSun, loadVpn])

  const wake = async () => {
    setWaking(true)
    const r = await remoteWake()
    setSun({ up: r.sunshine_up, host: r.host }); setWaking(false)
  }
  const ctl = async (action: string, location?: string) => {
    await vpnControl(action, location); setTimeout(loadVpn, 1500)
  }

  return (
    <motion.div className="absolute inset-0 z-20 flex flex-col panel"
      initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }} transition={{ duration: 0.2 }}>
      <div className="flex items-center justify-between px-4 py-3 border-b border-[rgba(0,212,255,0.15)]">
        <div className="flex items-center gap-2">
          <MonitorPlay size={14} className="text-[var(--cyan)]" />
          <span className="text-xs tracking-widest text-[var(--cyan)] glow-sm">BUREAU DISTANT & VPN</span>
        </div>
        <button onClick={onClose} className="text-[var(--text-dim)] hover:text-[var(--cyan)]"><X size={16} /></button>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-5 flex flex-col gap-6">
        {/* Streaming */}
        <section className="flex flex-col gap-3">
          <h3 className="text-[10px] tracking-widest text-[var(--text-dim)]">STREAMING (MOONLIGHT / SUNSHINE)</h3>
          <div className="flex items-center justify-between border border-[rgba(0,212,255,0.12)] rounded px-3 py-2">
            <span className="text-xs text-[var(--text)]">Sunshine sur {sun?.host ?? '…'}</span>
            <span className="flex items-center gap-1.5 text-[10px] tracking-widest"
              style={{ color: sun?.up ? '#00ffcc' : '#ff7a3b' }}>
              <span className="w-2 h-2 rounded-full" style={{ background: sun?.up ? '#00ffcc' : '#ff7a3b' }} />
              {sun?.up ? 'EN LIGNE' : 'HORS LIGNE'}
            </span>
          </div>
          <div className="flex gap-2">
            <button onClick={wake} disabled={waking}
              className="flex-1 flex items-center justify-center gap-2 py-2 rounded border border-[var(--cyan)] text-[var(--cyan)] text-[11px] tracking-widest hover:bg-[rgba(0,212,255,0.1)] disabled:opacity-50">
              {waking ? <Loader2 size={13} className="animate-spin" /> : <Power size={13} />}
              {waking ? 'RÉVEIL…' : 'RÉVEILLER KUBUNTU'}
            </button>
            <button onClick={loadSun} className="px-3 rounded border border-[rgba(0,212,255,0.2)] text-[var(--text-dim)] hover:text-[var(--cyan)]"><RefreshCw size={13} /></button>
          </div>
        </section>

        {/* VPN */}
        <section className="flex flex-col gap-3">
          <h3 className="text-[10px] tracking-widest text-[var(--text-dim)]">VPN MULLVAD</h3>
          {vpn && (
            <div className="border border-[rgba(0,212,255,0.12)] rounded px-3 py-2 flex flex-col gap-1">
              <span className="flex items-center gap-2 text-xs">
                <ShieldHalf size={13} style={{ color: vpn.protected ? '#00ffcc' : '#ff3b3b' }} />
                <span style={{ color: vpn.protected ? '#00ffcc' : '#ff3b3b' }}>
                  {vpn.protected ? 'Protégé' : 'Non protégé'}
                </span>
                <span className="text-[10px] text-[var(--text-dim)]">(sortie JARVIS)</span>
              </span>
              {vpn.ip && <span className="text-[10px] text-[var(--text-dim)]">IP {vpn.ip} · {vpn.loc}</span>}
              {vpn.ssh && <pre className="text-[9px] text-[var(--text-dim)] whitespace-pre-wrap">{vpn.ssh}</pre>}
            </div>
          )}
          <div className="flex gap-2">
            <button onClick={() => ctl('connect')}
              className="flex-1 py-2 rounded border border-[rgba(0,212,255,0.3)] text-[var(--cyan)] text-[10px] tracking-widest hover:bg-[rgba(0,212,255,0.08)]">CONNECTER</button>
            <button onClick={() => ctl('disconnect')}
              className="flex-1 py-2 rounded border border-red-500/40 text-red-400 text-[10px] tracking-widest hover:bg-red-500/10">DÉCONNECTER</button>
          </div>
          <p className="text-[9px] text-[var(--text-dim)] opacity-60">
            Contrôle réel : nécessite MULLVAD_SSH_HOST (hôte avec le CLI mullvad).
          </p>
        </section>
      </div>
    </motion.div>
  )
}
