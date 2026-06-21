'use client'

import { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Webhook as WebhookIcon, X, Trash2, Copy, Check, Plus } from 'lucide-react'
import { fetchHooks, createHook, deleteHook, hookUrl, Webhook } from '@/lib/api'

interface Props { onClose: () => void }

export default function HooksPanel({ onClose }: Props) {
  const [hooks, setHooks] = useState<Webhook[]>([])
  const [label, setLabel] = useState('')
  const [message, setMessage] = useState('')
  const [copied, setCopied] = useState<string>('')

  const load = useCallback(async () => setHooks(await fetchHooks()), [])
  useEffect(() => { load() }, [load])

  const add = async () => {
    if (!label.trim() || !message.trim()) return
    const h = await createHook(label.trim(), message.trim())
    if (h) { setLabel(''); setMessage(''); load() }
  }
  const remove = async (id: string) => {
    if (await deleteHook(id)) setHooks(h => h.filter(x => x.id !== id))
  }
  const copy = (token: string) => {
    navigator.clipboard?.writeText(hookUrl(token))
    setCopied(token); setTimeout(() => setCopied(''), 1500)
  }

  return (
    <motion.div
      className="absolute inset-0 z-20 flex flex-col panel"
      initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }} transition={{ duration: 0.2 }}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-[rgba(0,212,255,0.15)]">
        <div className="flex items-center gap-2">
          <WebhookIcon size={14} className="text-[var(--cyan)]" />
          <span className="text-xs tracking-widest text-[var(--cyan)] glow-sm">WEBHOOKS — DÉCLENCHEURS EXTERNES</span>
        </div>
        <button onClick={onClose} className="text-[var(--text-dim)] hover:text-[var(--cyan)]">
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-4">
        {/* Création */}
        <div className="flex flex-col gap-2 border border-[rgba(0,212,255,0.15)] rounded p-3">
          <p className="text-[10px] tracking-widest text-[var(--text-dim)]">NOUVEAU DÉCLENCHEUR</p>
          <input value={label} onChange={e => setLabel(e.target.value)}
            placeholder="Nom (ex. brief-matin)"
            className="bg-transparent border border-[rgba(0,212,255,0.2)] rounded px-3 py-1.5 text-sm
                       text-[var(--text)] outline-none focus:border-[var(--cyan)]" />
          <input value={message} onChange={e => setMessage(e.target.value)}
            placeholder="Message à exécuter (ex. résume mes nouveaux fichiers nextcloud)"
            className="bg-transparent border border-[rgba(0,212,255,0.2)] rounded px-3 py-1.5 text-sm
                       text-[var(--text)] outline-none focus:border-[var(--cyan)]" />
          <button onClick={add}
            className="flex items-center justify-center gap-2 px-3 py-1.5 rounded border border-[var(--cyan)]
                       text-[var(--cyan)] text-[11px] tracking-widest hover:bg-[rgba(0,212,255,0.1)]">
            <Plus size={13} /> CRÉER
          </button>
        </div>

        {/* Liste */}
        {hooks.length === 0 ? (
          <p className="text-[10px] text-[var(--text-dim)] text-center opacity-60">
            Aucun webhook. Crée-en un, puis appelle son URL depuis Home Assistant
            (action « RESTful Command » en POST) ou n'importe quel script.
          </p>
        ) : hooks.map(h => (
          <div key={h.id} className="border border-[rgba(0,212,255,0.12)] rounded px-3 py-2 flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs text-[var(--cyan)]">{h.label}</span>
              <button onClick={() => remove(h.id)} className="text-[var(--text-dim)] hover:text-red-400">
                <Trash2 size={13} />
              </button>
            </div>
            <span className="text-[11px] text-[var(--text-dim)]">▶ {h.message}</span>
            <div className="flex items-center gap-2">
              <code className="flex-1 text-[9px] text-[var(--text-dim)] bg-[rgba(0,212,255,0.05)] rounded px-2 py-1 truncate">
                POST {hookUrl(h.token)}
              </code>
              <button onClick={() => copy(h.token)}
                className="text-[var(--text-dim)] hover:text-[var(--cyan)] shrink-0">
                {copied === h.token ? <Check size={13} className="text-[#00ffcc]" /> : <Copy size={13} />}
              </button>
            </div>
            <span className="text-[9px] text-[var(--text-dim)] opacity-60">
              {h.run_count} déclenchement(s){h.last_triggered ? ` · dernier : ${h.last_triggered.slice(0, 16).replace('T', ' ')}` : ''}
            </span>
          </div>
        ))}
      </div>
    </motion.div>
  )
}
