'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { BarChart3, X, MessageSquare, Brain, CalendarClock, Image as ImageIcon, Database } from 'lucide-react'
import { fetchStats, UsageStats } from '@/lib/api'

interface Props { onClose: () => void }

export default function StatsPanel({ onClose }: Props) {
  const [s, setS] = useState<UsageStats | null>(null)

  useEffect(() => {
    fetchStats().then(setS)
    const id = setInterval(() => fetchStats().then(setS), 15000)
    return () => clearInterval(id)
  }, [])

  const maxAgent = Math.max(1, ...(s?.agent_usage.map(a => a.count) ?? [1]))
  const maxDay = Math.max(1, ...(s?.messages_per_day.map(d => d.count) ?? [1]))
  const toolTotal = (s?.tools.ok ?? 0) + (s?.tools.error ?? 0)
  const okPct = toolTotal ? Math.round((s!.tools.ok / toolTotal) * 100) : 0

  return (
    <motion.div
      className="absolute inset-0 z-20 flex flex-col panel"
      initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }} transition={{ duration: 0.2 }}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-[rgba(0,212,255,0.15)]">
        <div className="flex items-center gap-2">
          <BarChart3 size={14} className="text-[var(--cyan)]" />
          <span className="text-xs tracking-widest text-[var(--cyan)] glow-sm">STATISTIQUES D'USAGE</span>
        </div>
        <button onClick={onClose} className="text-[var(--text-dim)] hover:text-[var(--cyan)]">
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-5 flex flex-col gap-6">
        {!s ? (
          <p className="text-xs text-[var(--text-dim)] tracking-widest">CHARGEMENT…</p>
        ) : (
          <>
            {/* Totaux */}
            <div className="grid grid-cols-3 gap-2">
              <Stat icon={<MessageSquare size={14} />} label="MESSAGES" value={s.totals.messages} />
              <Stat icon={<Database size={14} />} label="SESSIONS" value={s.totals.sessions} />
              <Stat icon={<Brain size={14} />} label="FAITS" value={s.totals.facts} />
              <Stat icon={<CalendarClock size={14} />} label="TÂCHES" value={s.totals.tasks} />
              <Stat icon={<ImageIcon size={14} />} label="MÉDIAS" value={s.totals.media} />
              <Stat icon={<BarChart3 size={14} />} label="OUTILS OK" value={`${okPct}%`} />
            </div>

            {/* Agents les plus utilisés */}
            <section className="flex flex-col gap-2">
              <h3 className="text-[10px] tracking-widest text-[var(--text-dim)]">AGENTS LES PLUS SOLLICITÉS</h3>
              {s.agent_usage.length === 0 ? (
                <p className="text-[10px] text-[var(--text-dim)] opacity-60">Pas encore de données.</p>
              ) : s.agent_usage.map(a => (
                <div key={a.agent} className="flex items-center gap-2">
                  <span className="text-[10px] text-[var(--text-dim)] w-24 truncate">{a.agent}</span>
                  <div className="flex-1 h-3 bg-[rgba(0,212,255,0.06)] rounded overflow-hidden">
                    <div className="h-full bg-[var(--cyan)]" style={{ width: `${(a.count / maxAgent) * 100}%` }} />
                  </div>
                  <span className="text-[10px] text-[var(--cyan)] w-8 text-right">{a.count}</span>
                </div>
              ))}
            </section>

            {/* Activité 7 jours */}
            <section className="flex flex-col gap-2">
              <h3 className="text-[10px] tracking-widest text-[var(--text-dim)]">ACTIVITÉ (7 JOURS)</h3>
              <div className="flex items-end gap-1.5 h-24">
                {s.messages_per_day.length === 0 ? (
                  <p className="text-[10px] text-[var(--text-dim)] opacity-60">Pas encore de données.</p>
                ) : s.messages_per_day.map(d => (
                  <div key={d.day} className="flex-1 flex flex-col items-center gap-1">
                    <div className="w-full bg-[var(--cyan)] rounded-t" style={{ height: `${(d.count / maxDay) * 80}px` }} />
                    <span className="text-[8px] text-[var(--text-dim)]">{d.day.slice(5)}</span>
                  </div>
                ))}
              </div>
            </section>

            {/* Routage */}
            <section className="flex flex-col gap-2">
              <h3 className="text-[10px] tracking-widest text-[var(--text-dim)]">MÉTHODE DE ROUTAGE</h3>
              <div className="flex gap-2 flex-wrap">
                {s.method_breakdown.map(mb => (
                  <span key={mb.method} className="text-[10px] px-2 py-1 rounded border border-[rgba(0,212,255,0.2)] text-[var(--text-dim)]">
                    {mb.method} · <span className="text-[var(--cyan)]">{mb.count}</span>
                  </span>
                ))}
              </div>
            </section>

            {/* Outils */}
            {s.tools.top.length > 0 && (
              <section className="flex flex-col gap-2">
                <h3 className="text-[10px] tracking-widest text-[var(--text-dim)]">OUTILS LES PLUS APPELÉS</h3>
                {s.tools.top.map(t => (
                  <div key={t.tool} className="flex items-center justify-between text-[10px]">
                    <span className="text-[var(--text-dim)] font-mono">{t.tool}</span>
                    <span className="text-[var(--cyan)]">{t.count}</span>
                  </div>
                ))}
              </section>
            )}
          </>
        )}
      </div>
    </motion.div>
  )
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: number | string }) {
  return (
    <div className="flex flex-col gap-1 border border-[rgba(0,212,255,0.12)] rounded px-2 py-2">
      <span className="flex items-center gap-1 text-[8px] tracking-widest text-[var(--text-dim)]">{icon}{label}</span>
      <span className="text-xl text-[var(--cyan)] glow-sm">{value}</span>
    </div>
  )
}
