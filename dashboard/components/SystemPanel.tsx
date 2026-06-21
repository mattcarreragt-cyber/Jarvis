'use client'

import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { SlidersHorizontal, X, Server, Cpu, Cloud, Download, Upload } from 'lucide-react'
import { fetchSystem, downloadBackup, restoreBackup, SystemInfo } from '@/lib/api'

interface Props { onClose: () => void }

const STATUS_COLOR: Record<string, string> = {
  online: '#00ffcc', offline: '#ff4d4d', standby: '#ffcc00', disabled: '#3a5560',
}
const STATUS_LABEL: Record<string, string> = {
  online: 'EN LIGNE', offline: 'HORS LIGNE', standby: 'EN VEILLE', disabled: 'DÉSACTIVÉ',
}
const PALIER_ICON: Record<string, React.ReactNode> = {
  Unraid: <Server size={14} />, Kubuntu: <Cpu size={14} />, RunPod: <Cloud size={14} />,
}

export default function SystemPanel({ onClose }: Props) {
  const [info, setInfo] = useState<SystemInfo | null>(null)
  const [backupMsg, setBackupMsg] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    fetchSystem().then(setInfo)
    const id = setInterval(() => fetchSystem().then(setInfo), 10000)
    return () => clearInterval(id)
  }, [])

  const onRestore = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    setBackupMsg('Restauration…')
    const res = await restoreBackup(f, 'merge')
    setBackupMsg(res.ok ? 'Sauvegarde restaurée ✓' : `Échec : ${res.error}`)
  }

  return (
    <motion.div
      className="absolute inset-0 z-20 flex flex-col panel"
      initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }} transition={{ duration: 0.2 }}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-[rgba(0,212,255,0.15)]">
        <div className="flex items-center gap-2">
          <SlidersHorizontal size={14} className="text-[var(--cyan)]" />
          <span className="text-xs tracking-widest text-[var(--cyan)] glow-sm">SYSTÈME</span>
        </div>
        <button onClick={onClose} className="text-[var(--text-dim)] hover:text-[var(--cyan)]">
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-5 flex flex-col gap-6">
        {!info ? (
          <p className="text-xs text-[var(--text-dim)] tracking-widest">CHARGEMENT…</p>
        ) : (
          <>
            {/* Mode modèles */}
            <div className="flex items-center justify-between border border-[rgba(0,212,255,0.12)] rounded px-3 py-2">
              <span className="text-[10px] tracking-widest text-[var(--text-dim)]">MODE MODÈLES</span>
              <span className="text-[10px] tracking-widest"
                style={{ color: info.unrestricted_mode ? '#ffcc00' : '#4a7a96' }}>
                {info.unrestricted_mode ? 'SANS RESTRICTION' : 'STANDARD'}
              </span>
            </div>

            {/* Paliers */}
            <section className="flex flex-col gap-2">
              <h3 className="text-[10px] tracking-widest text-[var(--text-dim)]">PALIERS DE CALCUL</h3>
              {info.paliers.map(p => (
                <div key={p.name}
                  className="flex items-center gap-3 border border-[rgba(0,212,255,0.12)] rounded px-3 py-2">
                  <span className="text-[var(--cyan)]">{PALIER_ICON[p.name]}</span>
                  <div className="flex-1">
                    <p className="text-xs text-[var(--text)]">{p.name}</p>
                    <p className="text-[10px] text-[var(--text-dim)]">{p.role}</p>
                  </div>
                  <span className="flex items-center gap-1.5 text-[9px] tracking-widest"
                    style={{ color: STATUS_COLOR[p.status] }}>
                    <span className="w-2 h-2 rounded-full" style={{ background: STATUS_COLOR[p.status] }} />
                    {STATUS_LABEL[p.status]}
                  </span>
                </div>
              ))}
            </section>

            {/* Capacités */}
            <section className="flex flex-col gap-2">
              <h3 className="text-[10px] tracking-widest text-[var(--text-dim)]">
                CAPACITÉS & MODÈLES ({info.capabilities.length})
              </h3>
              {info.capabilities.map(c => (
                <div key={c.name}
                  className="flex items-center justify-between border border-[rgba(0,212,255,0.08)] rounded px-3 py-1.5">
                  <div>
                    <span className="text-xs text-[var(--cyan)]">{c.name}</span>
                    <span className="text-[10px] text-[var(--text-dim)] ml-2">{c.model}</span>
                  </div>
                  <span className="text-[9px] tracking-widest text-[var(--text-dim)]">
                    {c.machine.toUpperCase()}{c.vram_gb ? ` · ${c.vram_gb}GB` : ''}
                  </span>
                </div>
              ))}
            </section>

            {/* Agents */}
            <section className="flex flex-col gap-1">
              <h3 className="text-[10px] tracking-widest text-[var(--text-dim)]">
                AGENTS ({info.agents.length})
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {info.agents.map(a => (
                  <span key={a.name} title={a.description}
                    className="text-[10px] px-2 py-0.5 rounded border border-[rgba(0,212,255,0.2)] text-[var(--text-dim)]">
                    {a.name}
                  </span>
                ))}
              </div>
            </section>

            {/* Sauvegarde */}
            <section className="flex flex-col gap-2 border-t border-[rgba(0,212,255,0.1)] pt-4">
              <h3 className="text-[10px] tracking-widest text-[var(--text-dim)]">
                SAUVEGARDE (faits · tâches · webhooks)
              </h3>
              <div className="flex gap-2">
                <button onClick={() => downloadBackup()}
                  className="flex-1 flex items-center justify-center gap-1.5 py-1.5 text-[10px] tracking-widest
                             text-[var(--cyan)] border border-[rgba(0,212,255,0.3)] rounded hover:bg-[rgba(0,212,255,0.08)]">
                  <Download size={12} /> EXPORTER
                </button>
                <button onClick={() => fileRef.current?.click()}
                  className="flex-1 flex items-center justify-center gap-1.5 py-1.5 text-[10px] tracking-widest
                             text-[var(--text-dim)] border border-[rgba(0,212,255,0.2)] rounded hover:text-[var(--cyan)] hover:border-[var(--cyan)]">
                  <Upload size={12} /> RESTAURER
                </button>
                <input ref={fileRef} type="file" accept=".json" className="hidden" onChange={onRestore} />
              </div>
              {backupMsg && <p className="text-[10px] text-[var(--text-dim)] text-center">{backupMsg}</p>}
            </section>
          </>
        )}
      </div>
    </motion.div>
  )
}
