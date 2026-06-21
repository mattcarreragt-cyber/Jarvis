'use client'

import { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { ShieldCheck, X, Trash2, Plus, ScanLine, Loader2, Play } from 'lucide-react'
import {
  fetchCyberHosts, addCyberHost, deleteCyberHost, runCyberAudit, remediateCyber,
  CyberHost, CyberFinding,
} from '@/lib/api'

interface Props { onClose: () => void }

const SEV_COLOR: Record<string, string> = {
  critical: '#ff3b3b', high: '#ff7a3b', medium: '#ffcc00', low: '#3ba9ff', info: '#4a7a96',
}

export default function CyberPanel({ onClose }: Props) {
  const [hosts, setHosts] = useState<CyberHost[]>([])
  const [findings, setFindings] = useState<Record<string, CyberFinding[]>>({})
  const [scores, setScores] = useState<Record<string, { score: number; grade: string }>>({})
  const [auditing, setAuditing] = useState<string>('')
  const [form, setForm] = useState({ label: '', hostname: '', username: 'root', port: 22 })

  const load = useCallback(async () => setHosts(await fetchCyberHosts()), [])
  useEffect(() => { load() }, [load])

  const add = async () => {
    if (!form.label || !form.hostname) return
    if (await addCyberHost(form.label, form.hostname, form.username, Number(form.port))) {
      setForm({ label: '', hostname: '', username: 'root', port: 22 }); load()
    }
  }
  const audit = async (id: string) => {
    setAuditing(id)
    const res = await runCyberAudit(id)
    setAuditing('')
    if (res.ok && res.findings) {
      setFindings(f => ({ ...f, [id]: res.findings! }))
      if (res.score !== undefined && res.grade)
        setScores(s => ({ ...s, [id]: { score: res.score!, grade: res.grade! } }))
    } else alert(res.error || 'Audit impossible (SSH ?)')
  }
  const apply = async (id: string, cmd: string) => {
    if (!confirm(`Exécuter sur l'hôte :\n${cmd}`)) return
    const res = await remediateCyber(id, cmd)
    alert(res.ok ? `OK :\n${(res.output || '').slice(0, 500)}` : `Échec : ${res.error}`)
  }

  return (
    <motion.div
      className="absolute inset-0 z-20 flex flex-col panel"
      initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }} transition={{ duration: 0.2 }}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-[rgba(0,212,255,0.15)]">
        <div className="flex items-center gap-2">
          <ShieldCheck size={14} className="text-[var(--cyan)]" />
          <span className="text-xs tracking-widest text-[var(--cyan)] glow-sm">CYBERSÉCURITÉ — AUDIT DÉFENSIF</span>
        </div>
        <button onClick={onClose} className="text-[var(--text-dim)] hover:text-[var(--cyan)]">
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-4">
        {/* Ajout d'hôte */}
        <div className="flex flex-col gap-2 border border-[rgba(0,212,255,0.15)] rounded p-3">
          <p className="text-[10px] tracking-widest text-[var(--text-dim)]">AJOUTER UN HÔTE (TES MACHINES)</p>
          <div className="grid grid-cols-2 gap-2">
            <input value={form.label} onChange={e => setForm({ ...form, label: e.target.value })}
              placeholder="label (ex. unraid)" className="bg-transparent border border-[rgba(0,212,255,0.2)] rounded px-2 py-1 text-xs text-[var(--text)] outline-none focus:border-[var(--cyan)]" />
            <input value={form.hostname} onChange={e => setForm({ ...form, hostname: e.target.value })}
              placeholder="hostname / IP" className="bg-transparent border border-[rgba(0,212,255,0.2)] rounded px-2 py-1 text-xs text-[var(--text)] outline-none focus:border-[var(--cyan)]" />
            <input value={form.username} onChange={e => setForm({ ...form, username: e.target.value })}
              placeholder="utilisateur SSH" className="bg-transparent border border-[rgba(0,212,255,0.2)] rounded px-2 py-1 text-xs text-[var(--text)] outline-none focus:border-[var(--cyan)]" />
            <input value={form.port} onChange={e => setForm({ ...form, port: Number(e.target.value) })}
              type="number" placeholder="port" className="bg-transparent border border-[rgba(0,212,255,0.2)] rounded px-2 py-1 text-xs text-[var(--text)] outline-none focus:border-[var(--cyan)]" />
          </div>
          <button onClick={add} className="flex items-center justify-center gap-1.5 px-3 py-1.5 rounded border border-[var(--cyan)] text-[var(--cyan)] text-[11px] tracking-widest hover:bg-[rgba(0,212,255,0.1)]">
            <Plus size={13} /> AJOUTER
          </button>
          <p className="text-[9px] text-[var(--text-dim)] opacity-60">
            Auth par clé SSH (CYBER_SSH_KEY_PATH). Audit 100% lecture ; les correctifs
            ne s'appliquent que sur ton clic explicite.
          </p>
        </div>

        {/* Hôtes + findings */}
        {hosts.map(h => (
          <div key={h.id} className="border border-[rgba(0,212,255,0.12)] rounded p-3 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs text-[var(--cyan)]">{h.label}</span>
                <span className="text-[10px] text-[var(--text-dim)]">{h.username}@{h.hostname}:{h.port}</span>
                {scores[h.id] && (
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded"
                    style={{
                      color: scores[h.id].score >= 75 ? '#00ffcc' : scores[h.id].score >= 50 ? '#ffcc00' : '#ff3b3b',
                      border: `1px solid ${scores[h.id].score >= 75 ? '#00ffcc' : scores[h.id].score >= 50 ? '#ffcc00' : '#ff3b3b'}`,
                    }}>
                    {scores[h.id].score}/100 · {scores[h.id].grade}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => audit(h.id)} disabled={auditing === h.id}
                  className="flex items-center gap-1 text-[10px] tracking-widest text-[var(--cyan)] border border-[rgba(0,212,255,0.3)] rounded px-2 py-1 hover:bg-[rgba(0,212,255,0.08)]">
                  {auditing === h.id ? <Loader2 size={11} className="animate-spin" /> : <ScanLine size={11} />}
                  AUDITER
                </button>
                <button onClick={() => deleteCyberHost(h.id).then(load)} className="text-[var(--text-dim)] hover:text-red-400">
                  <Trash2 size={13} />
                </button>
              </div>
            </div>

            {findings[h.id]?.map((f, i) => (
              <div key={i} className="border-l-2 pl-2 py-1" style={{ borderColor: SEV_COLOR[f.severity] }}>
                <div className="flex items-center gap-2">
                  <span className="text-[9px] uppercase tracking-widest" style={{ color: SEV_COLOR[f.severity] }}>{f.severity}</span>
                  <span className="text-xs text-[var(--text)]">{f.title}</span>
                </div>
                {f.recommendation && <p className="text-[10px] text-[var(--text-dim)]">→ {f.recommendation}</p>}
                {f.remediation && (
                  <div className="flex items-center gap-2 mt-1">
                    <code className="flex-1 text-[9px] text-[var(--text-dim)] bg-[rgba(0,212,255,0.05)] rounded px-2 py-1 truncate">{f.remediation}</code>
                    <button onClick={() => apply(h.id, f.remediation!)} title="Appliquer (SSH)"
                      className="text-[var(--cyan)] hover:text-white shrink-0"><Play size={12} /></button>
                  </div>
                )}
              </div>
            ))}
          </div>
        ))}
        {hosts.length === 0 && (
          <p className="text-[10px] text-[var(--text-dim)] text-center opacity-60">
            Aucun hôte. Ajoute tes machines pour lancer des audits de sécurité.
          </p>
        )}
      </div>
    </motion.div>
  )
}
