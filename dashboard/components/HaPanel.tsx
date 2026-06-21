'use client'

import { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { House, X, Lightbulb, Thermometer, ToggleLeft, ToggleRight, RefreshCw } from 'lucide-react'
import { fetchHaStates, haToggle, HaState } from '@/lib/api'

interface Props { onClose: () => void }

export default function HaPanel({ onClose }: Props) {
  const [sensors, setSensors] = useState<HaState[]>([])
  const [lights, setLights] = useState<HaState[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    const [s, l, sw] = await Promise.all([
      fetchHaStates('sensor'), fetchHaStates('light'), fetchHaStates('switch'),
    ])
    setSensors(s.states.slice(0, 40))
    setLights([...l.states, ...sw.states])
    setLoading(false)
  }, [])

  useEffect(() => {
    load()
    const id = setInterval(load, 15000)
    return () => clearInterval(id)
  }, [load])

  const toggle = async (e: HaState) => {
    const on = !(e.state === 'on')
    setLights(ls => ls.map(x => x.entity_id === e.entity_id ? { ...x, state: on ? 'on' : 'off' } : x))
    await haToggle(e.entity_id, on)
  }

  return (
    <motion.div className="absolute inset-0 z-20 flex flex-col panel"
      initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }} transition={{ duration: 0.2 }}>
      <div className="flex items-center justify-between px-4 py-3 border-b border-[rgba(0,212,255,0.15)]">
        <div className="flex items-center gap-2">
          <House size={14} className="text-[var(--cyan)]" />
          <span className="text-xs tracking-widest text-[var(--cyan)] glow-sm">MAISON (HOME ASSISTANT)</span>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={load} className="text-[var(--text-dim)] hover:text-[var(--cyan)]"><RefreshCw size={13} /></button>
          <button onClick={onClose} className="text-[var(--text-dim)] hover:text-[var(--cyan)]"><X size={16} /></button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-6">
        {loading ? (
          <p className="text-xs text-[var(--text-dim)] tracking-widest">CHARGEMENT…</p>
        ) : (
          <>
            {/* Lumières / switches */}
            <section className="flex flex-col gap-2">
              <h3 className="flex items-center gap-1.5 text-[10px] tracking-widest text-[var(--text-dim)]">
                <Lightbulb size={11} /> LUMIÈRES & PRISES ({lights.length})
              </h3>
              {lights.length === 0 && <p className="text-[10px] text-[var(--text-dim)] opacity-60">Aucune entité (HA configuré ?).</p>}
              {lights.map(e => (
                <button key={e.entity_id} onClick={() => toggle(e)}
                  className="flex items-center justify-between border border-[rgba(0,212,255,0.12)] rounded px-3 py-1.5 hover:border-[var(--cyan)]">
                  <span className="text-xs text-[var(--text)]">{e.friendly_name || e.entity_id}</span>
                  {e.state === 'on'
                    ? <ToggleRight size={18} className="text-[#00ffcc]" />
                    : <ToggleLeft size={18} className="text-[var(--text-dim)]" />}
                </button>
              ))}
            </section>

            {/* Capteurs */}
            <section className="flex flex-col gap-2">
              <h3 className="flex items-center gap-1.5 text-[10px] tracking-widest text-[var(--text-dim)]">
                <Thermometer size={11} /> CAPTEURS ({sensors.length})
              </h3>
              {sensors.length === 0 && <p className="text-[10px] text-[var(--text-dim)] opacity-60">Aucun capteur.</p>}
              <div className="grid grid-cols-2 gap-2">
                {sensors.map(e => (
                  <div key={e.entity_id} className="border border-[rgba(0,212,255,0.1)] rounded px-2 py-1.5">
                    <p className="text-[10px] text-[var(--text-dim)] truncate">{e.friendly_name || e.entity_id}</p>
                    <p className="text-sm text-[var(--cyan)]">{e.state}</p>
                  </div>
                ))}
              </div>
            </section>
          </>
        )}
      </div>
    </motion.div>
  )
}
